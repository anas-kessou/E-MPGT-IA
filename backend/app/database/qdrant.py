"""
Qdrant Vector Database client — singleton with collection management.
"""

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import get_settings

logger = structlog.get_logger()

_client: QdrantClient | None = None

# Collection names
COLLECTION_DOCUMENTS = "documents_btp"
COLLECTION_NORMES = "normes_dtu"
COLLECTION_REX = "retours_experience"

ALL_COLLECTIONS = [COLLECTION_DOCUMENTS, COLLECTION_NORMES, COLLECTION_REX]


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client singleton."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=30,
        )
        logger.info("qdrant_connected", host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


def init_collections():
    """Create all required collections if they don't exist."""
    client = get_qdrant_client()
    settings = get_settings()

    for collection_name in ALL_COLLECTIONS:
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.embedding_dimensions,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("qdrant_collection_created", collection=collection_name)
        else:
            logger.info("qdrant_collection_exists", collection=collection_name)


def get_collection_info(collection_name: str) -> dict:
    """Get collection stats."""
    client = get_qdrant_client()
    try:
        info = client.get_collection(collection_name)
        return {
            "name": collection_name,
            "vectors_count": info.points_count, # Use points_count as a proxy for vectors in single-vector setups
            "points_count": info.points_count,
            "status": str(info.status),
        }
    except Exception as e:
        return {"name": collection_name, "error": str(e)}


def health_check() -> str:
    """Check if Qdrant is reachable."""
    try:
        client = get_qdrant_client()
        client.get_collections()
        return "healthy"
    except Exception:
        return "unhealthy"
