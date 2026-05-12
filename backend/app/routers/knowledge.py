"""
Knowledge Router — Knowledge Graph queries and visualization data.
"""

import structlog
from fastapi import APIRouter, Query
from typing import Optional

from app.services.knowledge_graph import (
    get_graph_overview,
    get_related_documents,
    get_norms_for_project,
    get_subgraph,
    get_global_graph,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Graph"])


@router.get("/overview")
async def knowledge_overview():
    """Get full knowledge graph statistics."""
    try:
        return get_graph_overview()
    except Exception as e:
        return {"nodes": {}, "relationships": {}, "error": str(e)}


@router.get("/graph/latest")
async def get_latest_graph(limit: int = Query(50, ge=10, le=100)):
    """Get a sample of the latest graph developments."""
    try:
        return get_global_graph(limit)
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}


@router.get("/related/{doc_id}")
async def get_related(doc_id: str, depth: int = Query(2, ge=1, le=4)):
    """Get documents related through shared norms, projects, or lots."""
    try:
        return get_related_documents(doc_id, depth)
    except Exception as e:
        return {"error": str(e)}


@router.get("/norms/{project_id}")
async def project_norms(project_id: str):
    """Get all norms referenced by documents in a project."""
    try:
        return get_norms_for_project(project_id)
    except Exception as e:
        return {"error": str(e)}


@router.get("/graph/{node_id}")
async def get_graph_data(
    node_id: str,
    node_type: str = Query("Document"),
    depth: int = Query(2, ge=1, le=4),
):
    """Get a subgraph centered on a specific node for visualization."""
    try:
        return get_subgraph(node_id, node_type, depth)
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}
