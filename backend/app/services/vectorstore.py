"""
Vector Store Service — Qdrant operations for semantic search.
Uses LangChain's QdrantVectorStore for embeddings + metadata filtering.
"""

import uuid
import structlog
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_core.documents import Document

from app.config import get_settings
from app.database.qdrant import (
    get_qdrant_client,
    COLLECTION_DOCUMENTS,
    COLLECTION_NORMES,
    COLLECTION_REX,
    ALL_COLLECTIONS,
)

logger = structlog.get_logger()

_embeddings = None
_vector_stores: dict[str, QdrantVectorStore] = {}


def get_embeddings():
    """Get or create embedding model singleton."""
    global _embeddings
    if _embeddings is None:
        settings = get_settings()
        _embeddings = GoogleGenerativeAIEmbeddings(model=settings.embedding_model)
        logger.info("embeddings_initialized", model=settings.embedding_model)
    return _embeddings


def get_vector_store(collection_name: str = COLLECTION_DOCUMENTS) -> QdrantVectorStore:
    """Get or create LangChain QdrantVectorStore for a collection."""
    global _vector_stores
    if collection_name not in _vector_stores:
        client = get_qdrant_client()
        embeddings = get_embeddings()
        _vector_stores[collection_name] = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
        )
        logger.info("vector_store_initialized", collection=collection_name)
    return _vector_stores[collection_name]


def add_documents(
    documents: list[Document],
    collection_name: str = COLLECTION_DOCUMENTS,
) -> list[str]:
    """Add documents with embeddings to a Qdrant collection."""
    store = get_vector_store(collection_name)
    ids = [str(uuid.uuid4()) for _ in documents]
    store.add_documents(documents, ids=ids)
    logger.info(
        "documents_added_to_qdrant",
        count=len(documents),
        collection=collection_name,
    )
    return ids


def semantic_search(
    query: str,
    collection_name: str = COLLECTION_DOCUMENTS,
    k: int = 5,
    project_id: str | None = None,
    document_type: str | None = None,
    doc_id: str | None = None,
) -> list[tuple[Document, float]]:
    """
    Perform semantic search with optional metadata filtering.
    Returns (document, score) tuples.
    """
    store = get_vector_store(collection_name)

    # Build filter conditions
    must_conditions = []
    if project_id:
        must_conditions.append(
            FieldCondition(key="metadata.project_id", match=MatchValue(value=project_id))
        )
    if document_type:
        must_conditions.append(
            FieldCondition(key="metadata.document_type", match=MatchValue(value=document_type))
        )
    if doc_id:
        must_conditions.append(
            FieldCondition(key="metadata.doc_id", match=MatchValue(value=doc_id))
        )

    search_filter = Filter(must=must_conditions) if must_conditions else None

    results = store.similarity_search_with_score(
        query,
        k=k,
        filter=search_filter,
    )

    logger.info(
        "semantic_search",
        query=query[:80],
        collection=collection_name,
        results=len(results),
    )
    return results


def get_retriever(
    collection_name: str = COLLECTION_DOCUMENTS,
    k: int = 5,
    project_id: str | None = None,
):
    """Get a LangChain retriever with optional metadata filtering."""
    store = get_vector_store(collection_name)

    search_kwargs = {"k": k}
    if project_id:
        search_kwargs["filter"] = Filter(
            must=[FieldCondition(key="metadata.project_id", match=MatchValue(value=project_id))]
        )

    return store.as_retriever(search_kwargs=search_kwargs)


def multi_collection_search(
    query: str,
    k_per_collection: int = 3,
    project_id: str | None = None,
    doc_id: str | None = None,
) -> list[tuple[Document, float, str]]:
    """Search across multiple collections and merge results."""
    all_results = []
    for collection_name in ALL_COLLECTIONS:
        try:
            results = semantic_search(
                query,
                collection_name=collection_name,
                k=k_per_collection,
                project_id=project_id,
                doc_id=doc_id,
            )
            for doc, score in results:
                all_results.append((doc, score, collection_name))
        except Exception as e:
            logger.warning("collection_search_error", collection=collection_name, error=str(e))

    # Sort by score (higher = more relevant)
    all_results.sort(key=lambda x: x[1], reverse=True)
    return all_results
