"""
Pydantic models for Projects and System health.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Project(BaseModel):
    """A BTP project."""
    id: Optional[str] = None
    name: str
    code: str  # e.g. "PRJ-2026-001"
    client: Optional[str] = None
    location: Optional[str] = None
    status: str = "actif"  # actif, terminé, en_pause
    lots: list[str] = []
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    documents_count: int = 0
    conformity_score: Optional[float] = None  # 0-100


class ProjectListResponse(BaseModel):
    projects: list[Project]
    total: int


class SystemHealth(BaseModel):
    """System status for all services."""
    status: str = "healthy"
    qdrant: str = "unknown"
    neo4j: str = "unknown"
    postgres: str = "unknown"
    minio: str = "unknown"
    llm: str = "unknown"
    documents_indexed: int = 0
    vectors_count: int = 0
    knowledge_nodes: int = 0
    uptime_seconds: float = 0.0


class DashboardStats(BaseModel):
    """Aggregated statistics for the dashboard."""
    total_documents: int = 0
    total_projects: int = 0
    total_vectors: int = 0
    total_queries_today: int = 0
    avg_conformity_score: float = 0.0
    documents_by_type: dict[str, int] = {}
    recent_activity: list[dict] = []
    data_sources_status: list[dict] = []
