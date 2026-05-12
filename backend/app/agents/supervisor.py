"""
Supervisor Agent — Routes queries to specialized agents
and orchestrates the full LangGraph pipeline.
"""

import time
import structlog
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.agents.state import AgentState
from app.agents.rag_agent import rag_node
from app.agents.conformity_agent import conformity_node

logger = structlog.get_logger()

# ── Intent Classification ──────────────────────────────────────────

CLASSIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un routeur intelligent pour un système IA BTP.
Classifie l'intention de la question parmi :
- question_technique : question sur des normes, DTU, techniques de construction
- verification_conformite : demande de vérification de conformité réglementaire
- synthese : demande de synthèse, résumé, ou rapport
- recherche_document : recherche d'un document spécifique

Réponds avec UN SEUL mot-clé parmi les 4 options ci-dessus. Rien d'autre."""),
    ("human", "{query}"),
])


async def classify_intent(state: AgentState) -> AgentState:
    """Classify user intent to route to the right agent."""
    settings = get_settings()
    llm = ChatGoogleGenerativeAI(model=settings.llm_model, temperature=0)
    chain = CLASSIFY_PROMPT | llm | StrOutputParser()

    try:
        intent = await chain.ainvoke({"query": state["user_query"]})
        intent = intent.strip().lower()
        # Validate intent
        valid = {"question_technique", "verification_conformite", "synthese", "recherche_document"}
        if intent not in valid:
            intent = "question_technique"
    except Exception:
        intent = "question_technique"

    state["intent"] = intent
    logger.info("intent_classified", intent=intent, query=state["user_query"][:60])
    return state


# ── Routing Function ───────────────────────────────────────────────

def route_by_intent(state: AgentState) -> str:
    """Route to the appropriate agent based on classified intent."""
    intent = state.get("intent", "question_technique")

    if intent == "verification_conformite":
        return "rag_then_conformity"
    elif intent == "synthese":
        return "rag_agent"
    elif intent == "recherche_document":
        return "rag_agent"
    else:  # question_technique
        return "rag_then_conformity"


# ── Build the Graph ────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    """
    Build the LangGraph agent pipeline:

    classify_intent → route
        → rag_agent → conformity_agent → END   (for technical / conformity)
        → rag_agent → END                       (for search / synthesis)
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("rag_agent", rag_node)
    workflow.add_node("conformity_agent", conformity_node)

    # Set entry point
    workflow.set_entry_point("classify_intent")

    # Conditional routing after classification
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "rag_then_conformity": "rag_agent",
            "rag_agent": "rag_agent",
        },
    )

    # After RAG, conditionally run conformity
    def should_check_conformity(state: AgentState) -> str:
        intent = state.get("intent", "")
        if intent in ("question_technique", "verification_conformite"):
            return "conformity_agent"
        return END

    workflow.add_conditional_edges(
        "rag_agent",
        should_check_conformity,
        {
            "conformity_agent": "conformity_agent",
            END: END,
        },
    )

    # Conformity always ends
    workflow.add_edge("conformity_agent", END)

    return workflow.compile()


# ── Singleton graph instance ───────────────────────────────────────

_graph = None


def get_agent_graph():
    """Get or create the compiled agent graph."""
    global _graph
    if _graph is None:
        _graph = build_agent_graph()
        logger.info("agent_graph_compiled")
    return _graph


async def run_agent(
    query: str,
    project_id: str | None = None,
    conversation_id: str | None = None,
) -> dict:
    """
    Execute the full agent pipeline on a user query.
    Returns a dict ready to be converted to ChatResponse.
    """
    start = time.time()

    initial_state: AgentState = {
        "user_query": query,
        "messages": [],
        "retrieved_docs": [],
        "kg_context": [],
        "intent": "",
        "response": "",
        "sources": [],
        "conformity_checks": [],
        "agent_used": "",
        "project_id": project_id,
        "processing_time_ms": 0,
    }

    graph = get_agent_graph()
    final_state = await graph.ainvoke(initial_state)

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "reply": final_state.get("response", "Désolé, je n'ai pas pu traiter votre demande."),
        "sources": final_state.get("sources", []),
        "conformity": final_state.get("conformity_checks", []),
        "agent_used": final_state.get("agent_used", "unknown"),
        "processing_time_ms": elapsed_ms,
        "intent": final_state.get("intent", "unknown"),
    }
