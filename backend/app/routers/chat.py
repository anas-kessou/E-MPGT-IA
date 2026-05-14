"""
Chat Router — Main AI conversation endpoint using LangGraph agents.
Performance-optimized: background query logging, deduplicated sources.
"""

import uuid
import asyncio
import structlog
from fastapi import APIRouter, HTTPException

from app.models.chat import ChatRequest, ChatResponse, SourceReference, ConformityCheck
from app.agents.supervisor import run_agent
from app.database.postgres import get_session, QueryLog

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["Chat"])


def _log_query_background(request_message, result):
    """Log query to PostgreSQL — runs in background thread."""
    try:
        session = get_session()
        log_record = QueryLog(
            id=str(uuid.uuid4()),
            user_query=request_message,
            agent_used=result.get("agent_used", "unknown"),
            response_summary=result["reply"][:500],
            sources_used=[{
                "doc": s.get("document_name"),
                "page": s.get("page_number")
            } for s in result.get("sources", [])],
            processing_time_ms=result.get("processing_time_ms", 0),
            project_id=None,
            conformity_issues=[{
                "norm": c.get("norm_reference"),
                "status": c.get("status")
            } for c in result.get("conformity", [])]
        )
        session.add(log_record)
        session.commit()
        session.close()
    except Exception as log_err:
        logger.warning("query_log_failed", error=str(log_err))


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint — Routes query through the LangGraph agent pipeline:
    1. Intent Classification (fast keyword first, then LLM)
    2. Multi-Query RAG Retrieval (parallel)
    3. Score-based Filtering (replaces LLM compression)
    4. Response Generation (strict grounding)
    5. Optional Conformity Verification
    """
    try:
        result = await run_agent(
            query=request.message,
            project_id=request.project_id,
            conversation_id=request.conversation_id,
        )

        sources = [
            SourceReference(
                document_name=s.get("document_name", "Inconnu"),
                page_number=s.get("page_number"),
                relevance_score=s.get("relevance_score", 0),
                document_type=s.get("document_type"),
                chunk_text=s.get("chunk_text"),
            )
            for s in result.get("sources", [])
        ]

        conformity = [
            ConformityCheck(
                norm_reference=c.get("norm_reference", "N/A"),
                status=c.get("status", "à vérifier"),
                detail=c.get("detail", ""),
                severity=c.get("severity", "info"),
            )
            for c in result.get("conformity", [])
        ]

        # Log query in background thread (non-blocking)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _log_query_background, request.message, result)

        return ChatResponse(
            reply=result["reply"],
            sources=sources,
            conformity=conformity,
            agent_used=result.get("agent_used", "unknown"),
            processing_time_ms=result.get("processing_time_ms", 0),
            conversation_id=request.conversation_id or str(uuid.uuid4()),
        )

    except Exception as e:
        logger.error("chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur IA: {str(e)}")
