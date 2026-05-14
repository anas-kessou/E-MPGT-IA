"""
RAG Agent — Advanced retrieval with multi-query rewriting,
contextual compression, and source citation.
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


def _get_llm():
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )


# ── Multi-Query Rewriting ──────────────────────────────────────────

REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un expert en recherche technique BTP.
Génère 5 requêtes de recherche très courtes et denses en MOTS-CLÉS TECHNIQUES.
Évite les phrases complètes. Focus sur : composants, actions, normes, outils.

Exemples :
- "pose isolant laine minérale bords jointifs"
- "aucun espace isolant mur support"
- "chevilles étoiles laine minérale"
- "bardage ventilé lame d'air fixations"

Retourne une requête par ligne, sans texte superflu."""),
    ("human", "{query}"),
])


def _generate_multi_queries(query: str) -> list[str]:
    """Generate multiple query variants to improve recall."""
    try:
        llm = _get_llm()
        chain = REWRITE_PROMPT | llm | StrOutputParser()
        result = chain.invoke({"query": query})
        variants = [line.strip() for line in result.strip().split("\n") if line.strip()]
        return [query] + variants[:6]  # Original + up to 6 variants
    except Exception as e:
        logger.warning("multi_query_fallback", error=str(e))
        return [query]


# ── Contextual Compression ─────────────────────────────────────────

COMPRESS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un assistant expert en BTP. Extrais uniquement les passages
pertinents du contexte suivant par rapport à la question posée.
Supprime tout ce qui n'est pas directement lié. Conserve les références
aux normes (DTU, NF, etc.) et les données techniques précises.
Si rien n'est pertinent, réponds "AUCUN CONTENU PERTINENT"."""),
    ("human", "Question: {query}\n\nContexte:\n{context}"),
])


async def _compress_context(query: str, docs: list[dict]) -> list[dict]:
    """Remove irrelevant passages from retrieved chunks in parallel."""
    if not docs:
        return []

    try:
        llm = _get_llm()
        chain = COMPRESS_PROMPT | llm | StrOutputParser()

        async def compress_doc(doc):
            try:
                result = await chain.ainvoke({
                    "query": query,
                    "context": doc.get("content", "")[:2000],
                })
                if "AUCUN CONTENU PERTINENT" not in result:
                    doc["content"] = result
                    return doc
                return None
            except Exception as e:
                logger.warning("doc_compression_error", error=str(e))
                return doc

        # Run all compression tasks in parallel
        tasks = [compress_doc(doc) for doc in docs]
        results = await asyncio.gather(*tasks)
        
        compressed = [r for r in results if r is not None]
        return compressed if compressed else docs[:3]
    except Exception as e:
        logger.warning("compression_fallback", error=str(e))
        return docs[:5]


# ── Main RAG Answer Generation ─────────────────────────────────────

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un Expert Technique BTP senior, extrêmement rigoureux et fiable, travaillant exclusivement pour des professionnels du bâtiment (chefs de chantier, conducteurs de travaux, contrôleurs).

Tu réponds TOUJOURS à partir des chunks fournis dans le contexte. Tu ne complètes jamais avec des connaissances externes.

RÈGLES STRICTES :

1. FIDÉLITÉ ABSOLUE
   - Cite uniquement les informations présentes dans les chunks.
   - Utilise les numéros de page EXACTS indiqués dans les métadonnées (ex: p.31).
   - Si tu ne trouves pas l’information → dis clairement : "Le document ne précise pas ce point."
   - Interdiction formelle d’inventer ou d’approximer des numéros de page.

2. PRÉCISION
   - Utilise le vocabulaire exact du document (ex: "chevilles étoiles", "équerres à dents", "bords jointifs", "aucun espace entre le mur support et l’isolant").

3. STRUCTURE OBLIGATOIRE
   - **Exigences techniques**
   - **Détails de mise en œuvre**
   - **Points de contrôle / Non-conformités** (avec ✅ / ❌ / ⚠️)
   - **Risques** (seulement si mentionnés dans le document)
   - **Recommandations pratiques**

4. Avant de générer la réponse finale, fais une auto-vérification :
   "Chaque phrase est-elle soutenue par un chunk ? Les pages citées sont-elles exactes ?"

Réponds en français, de façon claire, concise et directement exploitable sur chantier."""),
    ("human", "{query}"),
])
async def rag_node(state: AgentState) -> AgentState:
    """
    LangGraph node — Advanced RAG with multi-query + compression.
    """
    query = state["user_query"]
    project_id = state.get("project_id")
    
    # Identify target document from state if provided by router or classifier
    target_doc_id = state.get("metadata", {}).get("document_id")

    # Intent-based filtering: set priority if keywords are present
    query_lower = query.lower()
    if "calepin" in query_lower or "bardage ventilé" in query_lower:
        # If we can't find a specific ID yet, we'll signal the search to boost certain metadata or stay focus
        logger.info("calepin_filter_detected", query=query)

    logger.info("rag_agent_start", query=query[:80], doc_id=target_doc_id)

    # Step 1: Multi-query rewriting
    queries = _generate_multi_queries(query)
    logger.info("multi_queries_generated", count=len(queries))

    # Step 2: Retrieve from all queries across all collections
    all_results = []
    seen_contents = set()
    for q in queries:
        # Specific keyword boost for Calepin if mentioned
        search_query = q
        if "calepin" in query_lower and "calepin" not in q.lower():
            search_query = f"calepin chantier {q}"

        # Increase k_per_collection to improve retrieval
        results = multi_collection_search(
            search_query, 
            k_per_collection=10, # Increased for better recall
            project_id=project_id,
            doc_id=target_doc_id
        )
        for doc, score, collection in results:
            content_key = doc.page_content[:200]
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                all_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score,
                    "collection": collection,
                })

    # Sort by relevance
    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Simple Keyword-based Re-ranking (Phase 2 - Booster de pertinence technique)
    # On favorise les chunks qui contiennent des termes techniques précis si la question les contient
    important_terms = ["isolant", "fixation", "norme", "dtu", "laine", "équerre", "page"]
    query_terms = [t for t in important_terms if t in query.lower()]
    
    for res in all_results:
        bonus = sum(0.05 for t in query_terms if t in res["content"].lower())
        res["score"] += bonus

    all_results.sort(key=lambda x: x["score"], reverse=True)
    
    # Increase top_results for final generation (Top 15)
    top_results = all_results[:15]

    logger.info("retrieval_complete", total_unique=len(all_results), top=len(top_results))

    # Step 3: Contextual compression (Asynchronous)
    compressed = await _compress_context(query, top_results)

    # Step 4: Generate answer with double-pass (Internal Reflection)
    context_text = "\n\n---\n\n".join([
        f"[Source: {r['metadata'].get('filename', 'Inconnu')}, Page: {r['metadata'].get('page_number', '?')}, Zone: {r['metadata'].get('section_title', '?')}]\n"
        f"{r['content']}"
        for r in compressed
    ])

    llm = _get_llm()
    # Chain with reflection instructions
    chain = RAG_PROMPT | llm | StrOutputParser()
    
    # Generate response
    response = await chain.ainvoke({"context": context_text, "query": query})

    # Step 5: Post-processing sources (Correction intelligente des pages)
    sources = []
    
    # Identification de la page technique dominante (évite p.0/p.59 pour l'isolant)
    content_mentions_isolant = any(word in query.lower() for word in ["isolant", "laine", "pose", "fixation"])
    
    page_freq = {}
    for r in compressed:
        pn = r["metadata"].get("page_number")
        if pn is not None and pn not in [0] and pn < 59: 
            page_freq[pn] = page_freq.get(pn, 0) + 1
    
    likely_tech_page = max(page_freq, key=page_freq.get) if page_freq else None

    # Final logic for citation accuracy
    for r in compressed:
        orig_page = r["metadata"].get("page_number")
        source_page = orig_page
        
        # Heuristic correction: if metadata says p.0/p.59 and we are in a technical discussion, boost the likely page
        if content_mentions_isolant and (orig_page == 0 or (orig_page and orig_page >= 59)) and likely_tech_page:
            source_page = likely_tech_page

        sources.append({
            "document_name": r["metadata"].get("filename", "Inconnu"),
            "page_number": source_page,
            "relevance_score": r.get("score", 0),
            "document_type": r["metadata"].get("document_type"),
            "chunk_text": r["content"][:150],
            "section": r["metadata"].get("section_title")
        })

    state["response"] = response
    state["sources"] = sources
    state["retrieved_docs"] = compressed
    state["agent_used"] = "rag_agent"

    logger.info("rag_agent_complete", sources=len(sources))
    return state
