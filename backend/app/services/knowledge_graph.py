"""
Knowledge Graph Service — Neo4j operations for BTP knowledge.
Manages nodes: Projet, Document, Norme, Lot, Fournisseur, Decision, Risque.
"""

import structlog
from app.database.neo4j_client import run_query, get_stats

logger = structlog.get_logger()


# ── Node Creation ──────────────────────────────────────────────────

def create_document_node(doc_id: str, metadata: dict) -> None:
    """Create a Document node with its metadata in the knowledge graph."""
    run_query(
        """
        MERGE (d:Document {id: $id})
        SET d.filename = $filename,
            d.type = $type,
            d.lot = $lot,
            d.author = $author,
            d.date_indexed = datetime(),
            d.criticite = $criticite,
            d.num_pages = $num_pages
        """,
        {
            "id": doc_id,
            "filename": metadata.get("filename", ""),
            "type": metadata.get("document_type", "autre"),
            "lot": metadata.get("lot"),
            "author": metadata.get("author"),
            "criticite": metadata.get("criticite", "moyenne"),
            "num_pages": metadata.get("num_pages", 0),
        },
    )

    # Link to project if exists
    if metadata.get("project_id"):
        run_query(
            """
            MATCH (d:Document {id: $doc_id})
            MERGE (p:Projet {id: $project_id})
            MERGE (d)-[:APPARTIENT_A]->(p)
            """,
            {"doc_id": doc_id, "project_id": metadata["project_id"]},
        )

    # Link to norms if referenced
    for norm_ref in metadata.get("normes_references", []):
        run_query(
            """
            MATCH (d:Document {id: $doc_id})
            MERGE (n:Norme {reference: $norm_ref})
            ON CREATE SET n.type = $norm_type
            MERGE (d)-[:REFERENCE]->(n)
            """,
            {
                "doc_id": doc_id,
                "norm_ref": norm_ref,
                "norm_type": _classify_norm(norm_ref),
            },
        )

    # Link to lot if specified
    if metadata.get("lot"):
        run_query(
            """
            MATCH (d:Document {id: $doc_id})
            MERGE (l:Lot {id: $lot_id})
            ON CREATE SET l.name = $lot_name
            MERGE (d)-[:CONCERNE]->(l)
            """,
            {
                "doc_id": doc_id,
                "lot_id": metadata["lot"].lower().replace(" ", "_"),
                "lot_name": metadata["lot"],
            },
        )

    logger.info("kg_document_created", doc_id=doc_id, filename=metadata.get("filename"))


def create_project_node(project: dict) -> None:
    """Create or update a Project node."""
    run_query(
        """
        MERGE (p:Projet {id: $id})
        SET p.name = $name,
            p.code = $code,
            p.client = $client,
            p.location = $location,
            p.status = $status
        """,
        project,
    )


# ── Queries ────────────────────────────────────────────────────────

def get_related_documents(doc_id: str, depth: int = 2) -> list[dict]:
    """Find documents related through shared norms, projects, or lots."""
    return run_query(
        """
        MATCH (d:Document {id: $doc_id})-[*1..$depth]-(related:Document)
        WHERE related.id <> $doc_id
        RETURN DISTINCT related.id AS id,
               related.filename AS filename,
               related.type AS type
        LIMIT 10
        """,
        {"doc_id": doc_id, "depth": depth},
    )


def get_norms_for_project(project_id: str) -> list[dict]:
    """Get all norms referenced by documents in a project."""
    return run_query(
        """
        MATCH (p:Projet {id: $project_id})<-[:APPARTIENT_A]-(d:Document)-[:REFERENCE]->(n:Norme)
        RETURN DISTINCT n.reference AS reference, n.type AS type,
               count(d) AS document_count
        ORDER BY document_count DESC
        """,
        {"project_id": project_id},
    )


def get_graph_overview() -> dict:
    """Get full graph statistics for the dashboard."""
    stats = get_stats()
    relationships = run_query(
        """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(r) AS count
        ORDER BY count DESC
        """
    )
    return {
        "nodes": stats,
        "relationships": {r["type"]: r["count"] for r in relationships},
    }


def get_global_graph(limit: int = 50) -> dict:
    """Get a high-level view of the knowledge graph for visualization."""
    # Step 1: Fetch nodes
    node_results = run_query(
        """
        MATCH (n)
        RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS properties
        ORDER BY n.date_indexed DESC
        LIMIT $limit
        """,
        {"limit": limit}
    )

    # Step 2: Fetch relationships between those nodes
    edge_results = run_query(
        """
        MATCH (n)-[r]->(m)
        RETURN elementId(r) AS id, type(r) AS type,
               elementId(startNode(r)) AS start, elementId(endNode(r)) AS end
        LIMIT $limit
        """,
        {"limit": limit}
    )

    nodes = []
    for row in node_results:
        nodes.append({
            "id": row["id"],
            "labels": row["labels"],
            "properties": row["properties"]
        })

    edges = []
    for row in edge_results:
        edges.append({
            "id": row["id"],
            "type": row["type"],
            "start": row["start"],
            "end": row["end"]
        })

    return {"nodes": nodes, "edges": edges}


def get_subgraph(center_id: str, center_type: str = "Document", depth: int = 2) -> dict:
    """Get a subgraph centered on a node for visualization."""
    # Fetch connected nodes
    node_results = run_query(
        f"""
        MATCH path = (center:{center_type} {{id: $id}})-[*1..{depth}]-(neighbor)
        UNWIND nodes(path) AS n
        WITH DISTINCT n
        RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS properties
        """,
        {"id": center_id}
    )

    # Fetch relationships
    edge_results = run_query(
        f"""
        MATCH path = (center:{center_type} {{id: $id}})-[*1..{depth}]-(neighbor)
        UNWIND relationships(path) AS r
        WITH DISTINCT r
        RETURN elementId(r) AS id, type(r) AS type,
               elementId(startNode(r)) AS start, elementId(endNode(r)) AS end
        """,
        {"id": center_id}
    )

    nodes = [{"id": r["id"], "labels": r["labels"], "properties": r["properties"]} for r in node_results]
    edges = [{"id": r["id"], "type": r["type"], "start": r["start"], "end": r["end"]} for r in edge_results]

    return {"nodes": nodes, "edges": edges}

def _classify_norm(reference: str) -> str:
    """Classify a norm reference (DTU, NF, EN, ISO, etc.)."""
    ref_upper = reference.upper()
    if "DTU" in ref_upper:
        return "DTU"
    elif "NF" in ref_upper:
        return "NF"
    elif "EN" in ref_upper:
        return "EN"
    elif "ISO" in ref_upper:
        return "ISO"
    return "autre"
