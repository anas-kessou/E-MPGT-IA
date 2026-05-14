"""
RAG Agent — Advanced retrieval with multi-query rewriting,
score-based filtering, and strict source citation.

Performance-optimized: no per-document LLM compression,
parallel retrieval, cached LLM singleton.
"""

import asyncio
import structlog
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.agents.state import AgentState
from app.services.vectorstore import multi_collection_search, semantic_search
from app.database.qdrant import COLLECTION_DOCUMENTS

logger = structlog.get_logger()

# ── Cached LLM singleton ──────────────────────────────────────────

_llm_instance = None


def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        settings = get_settings()
        _llm_instance = ChatGoogleGenerativeAI(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )
    return _llm_instance


# ── Multi-Query Rewriting ──────────────────────────────────────────

REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un expert en recherche technique BTP.
Génère 3 requêtes de recherche très courtes et denses en MOTS-CLÉS TECHNIQUES.
Évite les phrases complètes. Focus sur : composants, actions, normes, outils.

Exemples :
- "pose isolant laine minérale bords jointifs"
- "chevilles étoiles laine minérale fixation"
- "bardage ventilé lame d'air fixations"

Retourne une requête par ligne, sans texte superflu."""),
    ("human", "{query}"),
])


async def _generate_multi_queries(query: str) -> list[str]:
    """Generate multiple query variants to improve recall (async)."""
    try:
        llm = _get_llm()
        chain = REWRITE_PROMPT | llm | StrOutputParser()
        result = await chain.ainvoke({"query": query})
        variants = [line.strip() for line in result.strip().split("\n") if line.strip()]
        return [query] + variants[:3]  # Original + up to 3 variants (was 6)
    except Exception as e:
        logger.warning("multi_query_fallback", error=str(e))
        return [query]


# ── Main RAG Answer Generation ─────────────────────────────────────

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un Expert Technique BTP senior, extrêmement rigoureux et fiable, travaillant exclusivement pour des professionnels du bâtiment (chefs de chantier, conducteurs de travaux, contrôleurs).

CONTEXTE DOCUMENTAIRE :
{context}

RÈGLES STRICTES :

1. FIDÉLITÉ ABSOLUE AU CONTEXTE
   - Réponds UNIQUEMENT à partir des chunks ci-dessus. JAMAIS de connaissances externes.
   - Chaque information doit être traçable à un chunk précis.
   - Si l'information n'est pas dans le contexte → dis clairement : "Le document ne précise pas ce point."
   - INTERDICTION FORMELLE d'inventer, d'approximer ou de déduire des informations.

2. CITATIONS DE PAGES — EXACTITUDE OBLIGATOIRE
   - Chaque chunk est accompagné de métadonnées [Source: fichier, Page: N].
   - Utilise UNIQUEMENT les numéros de page indiqués dans les métadonnées des chunks.
   - Format de citation : (Source: nom_fichier, p.N)
   - Si la page est indiquée comme "?" ou "0", cite simplement : (Source: nom_fichier) sans numéro de page.
   - NE JAMAIS inventer un numéro de page. Ne JAMAIS approximer.

3. PRÉCISION TECHNIQUE
   - Utilise le vocabulaire EXACT du document (ex: "chevilles étoiles", "équerres à dents", "bords jointifs").
   - Conserve les valeurs numériques exactes (dimensions, intensités, délais).
   - Cite les normes exactement comme elles apparaissent (DTU, NF, EN, etc.).

4. STRUCTURE OBLIGATOIRE
   - **Exigences techniques** (avec citations)
   - **Détails de mise en œuvre** (avec citations)
   - **Points de contrôle / Non-conformités** (avec ✅ / ❌ / ⚠️)
   - **Risques** (seulement si mentionnés dans le document)
   - **Recommandations pratiques**

5. AUTO-VÉRIFICATION AVANT RÉPONSE
   Avant de générer la réponse finale :
   - "Chaque phrase est-elle soutenue par un chunk ?"
   - "Les pages citées correspondent-elles EXACTEMENT aux métadonnées des chunks ?"
   - "Ai-je inventé ou approximé un numéro de page ? → Si oui, corriger ou supprimer."

Réponds en français, de façon claire, concise et directement exploitable sur chantier."""),
    ("human", "{query}"),
])


async def rag_node(state: AgentState) -> AgentState:
    """
    LangGraph node — Optimized RAG with multi-query + strict page citation.
    
    Pipeline:
    1. Multi-query rewriting (async, 3 variants)
    2. Parallel retrieval across all collections
    3. Score-based deduplication and filtering (no LLM compression)
    4. Response generation with strict grounding
    5. Honest source extraction from metadata
    """
    query = state["user_query"]
    project_id = state.get("project_id")
    target_doc_id = state.get("metadata", {}).get("document_id") if state.get("metadata") else None

    logger.info("rag_agent_start", query=query[:80], doc_id=target_doc_id)

    # Step 1: Multi-query rewriting (async)
    queries = await _generate_multi_queries(query)
    logger.info("multi_queries_generated", count=len(queries))

    # Step 2: Parallel retrieval across all queries
    all_results = []
    seen_contents = set()

    # Run searches concurrently using asyncio
    loop = asyncio.get_event_loop()
    search_tasks = []
    for q in queries:
        search_tasks.append(
            loop.run_in_executor(
                None,
                lambda q=q: multi_collection_search(
                    q,
                    k_per_collection=6,
                    project_id=project_id,
                    doc_id=target_doc_id,
                )
            )
        )
    
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    for results in search_results:
        if isinstance(results, Exception):
            logger.warning("search_task_error", error=str(results))
            continue
        for doc, score, collection in results:
            # Deduplicate by content prefix
            content_key = doc.page_content[:200]
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                all_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score,
                    "collection": collection,
                })

    # Sort by relevance score
    all_results.sort(key=lambda x: x["score"], reverse=True)

    # Step 3: Score-based filtering (replaces expensive LLM compression)
    # Keep top results with a minimum score threshold
    if all_results:
        max_score = all_results[0]["score"]
        # Keep results within 40% of the top score, up to 12 results
        score_threshold = max_score * 0.6
        filtered = [r for r in all_results if r["score"] >= score_threshold]
        top_results = filtered[:12]
    else:
        top_results = []

    logger.info("retrieval_complete", total_unique=len(all_results), top=len(top_results))

    # Step 4: Build context with EXACT metadata
    context_text = "\n\n---\n\n".join([
        f"[Source: {r['metadata'].get('filename', 'Inconnu')}, "
        f"Page: {r['metadata'].get('page_number', '?')}, "
        f"Zone: {r['metadata'].get('section_title', '?')}]\n"
        f"{r['content']}"
        for r in top_results
    ])

    if not context_text:
        context_text = "Aucun document pertinent trouvé dans la base vectorielle."

    # Step 5: Generate answer with strict grounding
    llm = _get_llm()
    chain = RAG_PROMPT | llm | StrOutputParser()
    response = await chain.ainvoke({"context": context_text, "query": query})

    # Step 6: Extract HONEST sources — NO heuristics, NO fabrication
    sources = []
    seen_source_keys = set()

    for r in top_results:
        raw_page = r["metadata"].get("page_number")
        filename = r["metadata"].get("filename", "Inconnu")
        
        # Use EXACT page number from metadata. No correction, no guessing.
        # Page 0 means metadata was missing during ingestion — report as None
        page_number = raw_page if (raw_page is not None and raw_page > 0) else None

        # Deduplicate sources by (filename, page) pair
        source_key = (filename, page_number)
        if source_key in seen_source_keys:
            continue
        seen_source_keys.add(source_key)

        sources.append({
            "document_name": filename,
            "page_number": page_number,
            "relevance_score": round(r.get("score", 0), 4),
            "document_type": r["metadata"].get("document_type"),
            "chunk_text": r["content"][:150],
            "section": r["metadata"].get("section_title"),
        })

    state["response"] = response
    state["sources"] = sources
    state["retrieved_docs"] = top_results
    state["agent_used"] = "rag_agent"

    logger.info("rag_agent_complete", sources=len(sources))
    return state
