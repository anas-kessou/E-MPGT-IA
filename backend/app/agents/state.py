"""
Shared Agent State — TypedDict used across all LangGraph nodes.
"""

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state flowing through the LangGraph agent pipeline."""

    # User's original query
    user_query: str

    # Messages for the conversation
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Retrieved documents from Qdrant
    retrieved_docs: list[dict]

    # Knowledge graph context from Neo4j
    kg_context: list[dict]

    # Agent classification result
    intent: str  # "question_technique", "verification_conformite", "synthese", "recherche_document"

    # Generated response
    response: str

    # Sources used in the response
    sources: list[dict]

    # Conformity checks performed
    conformity_checks: list[dict]
    
    # Claim Verification (Anti-Hallucination)
    verified_claims: list[dict]
    confidence: int

    # Which agent processed this
    agent_used: str

    # Optional project context
    project_id: str | None

    # Processing metadata
    processing_time_ms: int
