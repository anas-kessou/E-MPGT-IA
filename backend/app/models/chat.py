"""
Pydantic models for the Chat API.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    message: str = Field(..., min_length=1, max_length=5000, description="User question")
    project_id: Optional[str] = Field(default=None, description="Filter by project")
    conversation_id: Optional[str] = Field(default=None, description="Conversation thread ID")


class SourceReference(BaseModel):
    """A source document referenced in the AI response."""
    document_name: str
    page_number: Optional[int] = None
    chunk_text: Optional[str] = None
    relevance_score: float = 0.0
    document_type: Optional[str] = None


class ConformityCheck(BaseModel):
    """Conformity verification result from the conformity agent."""
    norm_reference: str
    status: str  # "conforme", "non-conforme", "à vérifier"
    detail: str
    severity: str = "info"  # "info", "warning", "critical"


class ChatResponse(BaseModel):
    """AI response with sources and metadata."""
    reply: str
    sources: list[SourceReference] = []
    conformity: list[ConformityCheck] = []
    agent_used: str = "rag_agent"
    processing_time_ms: int = 0
    conversation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
