"""
Conformity Agent — Verifies responses against DTU norms and regulations.
Uses LLM-as-a-Judge pattern for double verification.
"""

import structlog
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import get_settings
from app.agents.state import AgentState

logger = structlog.get_logger()

CONFORMITY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un expert vérificateur de conformité BTP. Ton rôle est d'analyser
une réponse technique et de vérifier si elle est conforme aux normes et DTU applicables.

Pour chaque point technique mentionné dans la réponse, tu dois :
1. Identifier la norme ou le DTU applicable
2. Vérifier si la recommandation est conforme
3. Signaler toute non-conformité ou risque

Réponds STRICTEMENT au format suivant (une vérification par ligne) :
NORME: [référence] | STATUT: [conforme/non-conforme/à vérifier] | SÉVÉRITÉ: [info/warning/critical] | DÉTAIL: [explication]

Si aucune vérification n'est possible, réponds : AUCUNE_VERIFICATION_POSSIBLE

CONTEXTE DOCUMENTAIRE :
{context}"""),
    ("human", """Question initiale : {query}

Réponse à vérifier :
{response}"""),
])


async def conformity_node(state: AgentState) -> AgentState:
    """
    LangGraph node — Verify conformity of the RAG response.
    """
    query = state["user_query"]
    response = state.get("response", "")
    retrieved_docs = state.get("retrieved_docs", [])

    if not response:
        return state

    logger.info("conformity_check_start", query=query[:80])

    # Build context from retrieved docs
    context_text = "\n\n".join([
        f"[{r['metadata'].get('filename', 'Inconnu')}] {r['content'][:500]}"
        for r in retrieved_docs
    ])

    settings = get_settings()
    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        temperature=0,  # Deterministic for conformity checks
    )

    chain = CONFORMITY_PROMPT | llm | StrOutputParser()

    try:
        result = await chain.ainvoke({
            "context": context_text,
            "query": query,
            "response": response,
        })

        checks = _parse_conformity_result(result)
        state["conformity_checks"] = checks

        # Count issues
        issues = [c for c in checks if c["status"] != "conforme"]
        if issues:
            logger.warning("conformity_issues_found", count=len(issues))
        else:
            logger.info("conformity_ok", checks=len(checks))

    except Exception as e:
        logger.error("conformity_check_error", error=str(e))
        state["conformity_checks"] = []

    return state


def _parse_conformity_result(result: str) -> list[dict]:
    """Parse the structured conformity check output."""
    if "AUCUNE_VERIFICATION_POSSIBLE" in result:
        return []

    checks = []
    for line in result.strip().split("\n"):
        line = line.strip()
        if not line or "NORME:" not in line:
            continue

        try:
            parts = {}
            for segment in line.split("|"):
                segment = segment.strip()
                if ":" in segment:
                    key, value = segment.split(":", 1)
                    parts[key.strip().lower()] = value.strip()

            checks.append({
                "norm_reference": parts.get("norme", "N/A"),
                "status": parts.get("statut", "à vérifier"),
                "severity": parts.get("sévérité", "info"),
                "detail": parts.get("détail", ""),
            })
        except Exception:
            continue

    return checks
