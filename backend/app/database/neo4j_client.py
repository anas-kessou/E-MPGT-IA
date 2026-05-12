"""
Neo4j Knowledge Graph client — driver management and schema initialization.
"""

import structlog
from neo4j import GraphDatabase
from app.config import get_settings

logger = structlog.get_logger()

_driver = None


def get_neo4j_driver():
    """Get or create Neo4j driver singleton."""
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        logger.info("neo4j_connected", uri=settings.neo4j_uri)
    return _driver


def init_schema():
    """Create constraints and indexes for our BTP knowledge graph."""
    driver = get_neo4j_driver()

    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Projet) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Norme) REQUIRE n.reference IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (l:Lot) REQUIRE l.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Fournisseur) REQUIRE f.name IS UNIQUE",
    ]

    indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.type)",
        "CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.date_indexed)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Norme) ON (n.type)",
        "CREATE INDEX IF NOT EXISTS FOR (p:Projet) ON (p.status)",
    ]

    with driver.session() as session:
        for constraint in constraints:
            try:
                session.run(constraint)
            except Exception as e:
                logger.warning("neo4j_constraint_skip", query=constraint, error=str(e))

        for index in indexes:
            try:
                session.run(index)
            except Exception as e:
                logger.warning("neo4j_index_skip", query=index, error=str(e))

    logger.info("neo4j_schema_initialized")


def run_query(query: str, params: dict = None) -> list[dict]:
    """Execute a Cypher query and return results as list of dicts."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


def health_check() -> str:
    """Check if Neo4j is reachable."""
    try:
        driver = get_neo4j_driver()
        driver.verify_connectivity()
        return "healthy"
    except Exception:
        return "unhealthy"


def get_stats() -> dict:
    """Get knowledge graph statistics."""
    try:
        results = run_query(
            """
            MATCH (n)
            RETURN labels(n)[0] AS label, count(n) AS count
            ORDER BY count DESC
            """
        )
        return {r["label"]: r["count"] for r in results}
    except Exception:
        return {}
