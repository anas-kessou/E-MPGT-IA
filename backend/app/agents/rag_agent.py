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
    ("system", """Tu es un assistant expert en BTP. Pour améliorer la recherche documentaire,
réécris la question de l'utilisateur en 3 variantes différentes qui couvrent
différents angles du sujet. Retourne exactement 3 lignes, une par variante.
Ne numérote pas les lignes. Pas d'explication."""),
    ("human", "{query}"),
])


def _generate_multi_queries(query: str) -> list[str]:
    """Generate multiple query variants to improve recall."""
    try:
        llm = _get_llm()
        chain = REWRITE_PROMPT | llm | StrOutputParser()
        result = chain.invoke({"query": query})
        variants = [line.strip() for line in result.strip().split("\n") if line.strip()]
        return [query] + variants[:3]  # Original + up to 3 variants
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
    ("system", """Tu es un expert en BTP (Bâtiment et Travaux Publics) et en réglementation
française de la construction. Tu maîtrises les DTU, normes NF, réglementations
CSTB, et les bonnes pratiques de chantier.

RÈGLES STRICTES :
1. Utilise UNIQUEMENT les documents fournis dans le contexte pour répondre.
2. Si tu ne trouves pas l'information dans le contexte, dis-le clairement.
3. Cite TOUJOURS tes sources avec le nom du document et la page si disponible.
4. Utilise un langage technique précis et professionnel.
5. Structure ta réponse avec des titres et des puces pour la lisibilité.
6. Si une norme DTU ou NF est mentionnée, cite la référence exacte.
7. Signale tout risque de non-conformité que tu identifies.

Format des citations : [Source: nom_du_document, p.X]

CONTEXTE DOCUMENTAIRE :
{context}"""),
    ("human", "{query}"),
])


async def rag_node(state: AgentState) -> AgentState:
    """
    LangGraph node — Advanced RAG with multi-query + compression.
    """
    query = state["user_query"]
    project_id = state.get("project_id")

    logger.info("rag_agent_start", query=query[:80])

    # Step 1: Multi-query rewriting
    queries = _generate_multi_queries(query)
    logger.info("multi_queries_generated", count=len(queries))

    # Step 2: Retrieve from all queries across all collections
    all_results = []
    seen_contents = set()
    for q in queries:
        results = multi_collection_search(q, k_per_collection=3, project_id=project_id)
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
    top_results = all_results[:10]

    logger.info("retrieval_complete", total_unique=len(all_results), top=len(top_results))

    # Step 3: Contextual compression (Asynchronous)
    compressed = await _compress_context(query, top_results)

    # Step 4: Generate answer
    context_text = "\n\n---\n\n".join([
        f"[Document: {r['metadata'].get('filename', 'Inconnu')}, "
        f"Page: {r['metadata'].get('page', '?')}, "
        f"Type: {r['metadata'].get('document_type', '?')}]\n"
        f"{r['content']}"
        for r in compressed
    ])

    llm = _get_llm()
    chain = RAG_PROMPT | llm | StrOutputParser()
    response = await chain.ainvoke({"context": context_text, "query": query})

    # Build source references
    sources = []
    for r in compressed:
        sources.append({
            "document_name": r["metadata"].get("filename", "Inconnu"),
            "page_number": r["metadata"].get("page"),
            "relevance_score": r.get("score", 0),
            "document_type": r["metadata"].get("document_type"),
            "chunk_text": r["content"][:150],
        })

    state["response"] = response
    state["sources"] = sources
    state["retrieved_docs"] = compressed
    state["agent_used"] = "rag_agent"

    logger.info("rag_agent_complete", sources=len(sources))
    return state
