"""
Health & Dashboard Router — System health checks and aggregated KPIs.
"""

import time
import structlog
from fastapi import APIRouter

from app.models.project import SystemHealth, DashboardStats
from app.database.qdrant import health_check as qdrant_health, get_collection_info, ALL_COLLECTIONS
from app.database.neo4j_client import health_check as neo4j_health, get_stats as neo4j_stats
from app.database.postgres import health_check as pg_health, get_session, DocumentRecord, QueryLog
from app.database.minio_client import health_check as minio_health
from datetime import datetime, date, timedelta

logger = structlog.get_logger()

_start_time = time.time()

router = APIRouter(prefix="/api", tags=["System"])


@router.get("/health", response_model=SystemHealth)
async def health_check():
    """Check the health of all connected services."""
    return SystemHealth(
        status="healthy",
        qdrant=qdrant_health(),
        neo4j=neo4j_health(),
        postgres=pg_health(),
        minio=minio_health(),
        llm="configured",
        uptime_seconds=round(time.time() - _start_time, 1),
    )


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats():
    """Get aggregated statistics for the dashboard."""
    session = get_session()
    try:
        # Documents count
        total_docs = session.query(DocumentRecord).count()

        # Documents by type
        type_counts = {}
        for record in session.query(DocumentRecord.document_type).distinct():
            dtype = record[0] or "autre"
            count = session.query(DocumentRecord).filter_by(document_type=dtype).count()
            type_counts[dtype] = count

        # Projects count (unique project_ids)
        project_ids = session.query(DocumentRecord.project_id).filter(
            DocumentRecord.project_id.isnot(None)
        ).distinct().count()

        # Vector counts
        total_vectors = 0
        for collection in ALL_COLLECTIONS:
            try:
                info = get_collection_info(collection)
                total_vectors += info.get("vectors_count", 0) or 0
            except Exception:
                pass

        # KG node count
        try:
            kg_stats = neo4j_stats()
            kg_nodes = sum(kg_stats.values())
        except Exception:
            kg_nodes = 0

        # Recent documents
        recent = session.query(DocumentRecord).order_by(
            DocumentRecord.date_indexed.desc()
        ).limit(10).all()

        recent_activity = [
            {
                "type": "document_indexed",
                "filename": r.filename,
                "document_type": r.document_type,
                "timestamp": str(r.date_indexed),
                "chunks": r.num_chunks or 0,
            }
            for r in recent
        ]

        # Data sources status
        data_sources = [
            {"name": "Qdrant (Vecteurs)", "status": qdrant_health(), "count": total_vectors},
            {"name": "Neo4j (Graphe)", "status": neo4j_health(), "count": kg_nodes},
            {"name": "PostgreSQL (Métadonnées)", "status": pg_health(), "count": total_docs},
            {"name": "MinIO (Documents)", "status": minio_health(), "count": total_docs},
        ]

        # Query Statistics
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        total_queries_today = session.query(QueryLog).filter(
            QueryLog.timestamp >= start_of_day
        ).count()

        # Average Conformity Score
        # We define a simple score: 100% - (% of queries with non-conforme issues)
        total_logs = session.query(QueryLog).count()
        if total_logs > 0:
            # Count logs that have at least one "non-conforme" issue
            # Since conformity_issues is JSON, we use a simple approach for now
            # In production, we might want a more granular score
            conformity_data = session.query(QueryLog.conformity_issues).all()
            total_issues_found = 0
            for (issues,) in conformity_data:
                if issues and any(i.get("status") == "non-conforme" for i in issues):
                    total_issues_found += 1
            
            avg_conformity_score = round(((total_logs - total_issues_found) / total_logs) * 100, 1)
        else:
            avg_conformity_score = 100.0

        return DashboardStats(
            total_documents=total_docs,
            total_projects=project_ids,
            total_vectors=total_vectors,
            total_queries_today=total_queries_today,
            avg_conformity_score=avg_conformity_score,
            documents_by_type=type_counts,
            recent_activity=recent_activity,
            data_sources_status=data_sources,
        )
    except Exception as e:
        logger.error("dashboard_stats_error", error=str(e))
        return DashboardStats()
    finally:
        session.close()
