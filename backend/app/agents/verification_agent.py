"""
Verification Agent — Extracts claims from generated response,
verifies them against the retrieved context, and computes confidence scores.
Also detects numeric claims (thresholds, percentages) for stricter validation.
"""

import re
import structlog
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.config import get_settings
from app.agents.state import AgentState

logger = structlog.get_logger()

# ── Cached LLM singleton ──────────────────────────────────────────

_verifier_llm = None


def _get_verifier_llm():
    global _verifier_llm
    if _verifier_llm is None:
        settings = get_settings()
        _verifier_llm = ChatGoogleGenerativeAI(
            model=settings.llm_model,
            temperature=0,  # Zero for deterministic verification
        )
    return _verifier_llm


VERIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un expert intraitable d'un bureau de contrôle BTP. Ton rôle est d'analyser la réponse générée face aux documents sources (chunks) extraits.

CONTEXTE DOCUMENTAIRE RÉEL:
{context}

RÉPONSE À VÉRIFIER:
{response}

TA TÂCHE:
1. Extraire les affirmations fortes (claims) de la réponse (particulièrement les chiffres, pourcentages, obligations, interdictions).
2. Pour chaque affirmation, rechercher la preuve sémantique exacte dans le CONTEXTE.
3. Assigner un statut: "SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED".
4. Calculer la confiance globale (0 à 100) en pénalisant très lourdement les affirmations UNSUPPORTED.
5. Générer une version RÉVISÉE de la réponse qui SUPPRIME OU CORRIGE toutes les affirmations non supportées, et utilise un format structuré expert.

Tu dois répondre UNIQUEMENT au format JSON avec cette structure exacte:
{{
  "claims": [
    {{
      "statement": "L'humidité doit être inférieure à 80%",
      "status": "UNSUPPORTED",
      "explanation": "Le contexte ne mentionne aucun seuil de 80%."
    }}
  ],
  "confidence_score": 45,
  "revised_response": "La réponse experte et purgée d'hallucinations ici..."
}}"""),
])

def _detect_numeric_risk(text: str) -> bool:
    """Detect if the text contains high-risk technical constraints."""
    pattern = r"\d+%|\d+\s*[cCmMm²³]|\dobligatoire|interdit|doit|dtu impose|norme exige"
    return bool(re.search(pattern, text.lower()))

async def verification_node(state: AgentState) -> AgentState:
    """
    LangGraph node — Claim Extraction, Verification & Confidence Scoring.
    """
    response = state.get("response", "")
    retrieved_docs = state.get("retrieved_docs", [])
    
    if not response or not retrieved_docs:
        state["confidence"] = 0
        state["verified_claims"] = []
        return state

    logger.info("verification_start")

    # Build context
    context_text = "\n\n---\n\n".join([
        f"[Source: {r['metadata'].get('filename', 'Inconnu')}]\n{r['content']}"
        for r in retrieved_docs
    ])

    llm = _get_verifier_llm()
    parser = JsonOutputParser()
    chain = VERIFICATION_PROMPT | llm | parser

    try:
        result = await chain.ainvoke({
            "context": context_text,
            "response": response,
        })

        claims = result.get("claims", [])
        score = result.get("confidence_score", 0)
        revised = result.get("revised_response", response)

        # Force score drop if numerical high-risk claims are unsupported
        for c in claims:
            if c.get("status") == "UNSUPPORTED" and _detect_numeric_risk(c.get("statement", "")):
                score = min(score, 30)  # Heavy penalty for hallucinated thresholds
                logger.warning("numeric_hallucination_detected", claim=c["statement"])

        state["verified_claims"] = claims
        state["confidence"] = score
        state["response"] = revised  # Override response with the verified structured one

        logger.info("verification_complete", score=score, claims=len(claims))
    except Exception as e:
        logger.error("verification_error", error=str(e))
        state["verified_claims"] = []
        state["confidence"] = 50  # fallback

    return state
