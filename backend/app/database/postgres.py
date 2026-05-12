"""
PostgreSQL database — SQLAlchemy models and session management.
"""

import structlog
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

logger = structlog.get_logger()

Base = declarative_base()
_engine = None
_SessionLocal = None


class DocumentRecord(Base):
    """Relational record for document metadata — searchable and filterable."""
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False, index=True)
    document_type = Column(String, default="autre", index=True)
    project_id = Column(String, nullable=True, index=True)
    project_name = Column(String, nullable=True)
    lot = Column(String, nullable=True)
    author = Column(String, nullable=True)
    date_document = Column(DateTime, nullable=True)
    date_indexed = Column(DateTime, default=datetime.utcnow)
    criticite = Column(String, default="moyenne")
    status = Column(String, default="pending", index=True)
    num_pages = Column(Integer, default=0)
    num_chunks = Column(Integer, default=0)
    file_size_bytes = Column(Integer, default=0)
    minio_path = Column(String, nullable=True)
    version = Column(Integer, default=1)
    tags = Column(JSON, default=list)
    normes_references = Column(JSON, default=list)
    content_hash = Column(String, nullable=True, unique=True)


class ProjectRecord(Base):
    """Project metadata."""
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True)
    client = Column(String, nullable=True)
    location = Column(String, nullable=True)
    status = Column(String, default="actif")
    lots = Column(JSON, default=list)
    date_start = Column(DateTime, nullable=True)
    date_end = Column(DateTime, nullable=True)
    conformity_score = Column(Float, nullable=True)


class QueryLog(Base):
    """Audit log for all queries (traçabilité complète)."""
    __tablename__ = "query_logs"

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_query = Column(Text, nullable=False)
    agent_used = Column(String, nullable=True)
    response_summary = Column(Text, nullable=True)
    sources_used = Column(JSON, default=list)
    processing_time_ms = Column(Integer, default=0)
    project_id = Column(String, nullable=True)
    conformity_issues = Column(JSON, default=list)


class SystemSettings(Base):
    """System-wide configuration persistence."""
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.postgres_url, pool_pre_ping=True)
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_database():
    """Create all tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("postgres_tables_created")


def health_check() -> str:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "healthy"
    except Exception:
        return "unhealthy"


# Need this import for health_check
from sqlalchemy import text
