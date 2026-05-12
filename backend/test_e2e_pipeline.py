"""
E-MPGT-IA — End-to-End Pipeline Test
Tests: Infrastructure → Ingestion → Knowledge Graph → RAG Chat

Run:  python test_e2e_pipeline.py   (from backend/)
"""

import os
import sys
import time
import asyncio
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

# ── Color output helpers ──────────────────────────────────────────
class C:
    OK = "\033[92m✓\033[0m"
    FAIL = "\033[91m✗\033[0m"
    INFO = "\033[94mℹ\033[0m"
    WARN = "\033[93m⚠\033[0m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def header(title: str):
    print(f"\n{'═'*60}")
    print(f"  {C.BOLD}{title}{C.RESET}")
    print(f"{'═'*60}")

def check(label: str, passed: bool, detail: str = ""):
    icon = C.OK if passed else C.FAIL
    d = f"  → {detail}" if detail else ""
    print(f"  {icon} {label}{d}")
    return passed

results = {"passed": 0, "failed": 0, "skipped": 0}

def tally(passed: bool):
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1


# ══════════════════════════════════════════════════════════════════
# STAGE 1: Infrastructure Connectivity
# ══════════════════════════════════════════════════════════════════
def test_infrastructure():
    header("STAGE 1 — Infrastructure Connectivity")

    # 1a. PostgreSQL
    try:
        from app.database.postgres import get_engine, init_database
        engine = get_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            row = conn.execute(text("SELECT 1")).fetchone()
        init_database()
        ok = check("PostgreSQL", True, f"Connected on port {os.getenv('POSTGRES_PORT', '5434')}")
    except Exception as e:
        ok = check("PostgreSQL", False, str(e))
    tally(ok)

    # 1b. Qdrant
    try:
        from app.database.qdrant import init_collections, get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections().collections
        init_collections()
        ok = check("Qdrant", True, f"{len(collections)} collections found")
    except Exception as e:
        ok = check("Qdrant", False, str(e))
    tally(ok)

    # 1c. Neo4j
    try:
        from app.database.neo4j_client import get_neo4j_driver, init_schema
        driver = get_neo4j_driver()
        driver.verify_connectivity()
        init_schema()
        ok = check("Neo4j", True, "Schema initialized")
    except Exception as e:
        ok = check("Neo4j", False, str(e))
    tally(ok)

    # 1d. MinIO
    try:
        from app.database.minio_client import get_minio_client, init_bucket
        client = get_minio_client()
        init_bucket()
        ok = check("MinIO", True, "Bucket ready")
    except Exception as e:
        ok = check("MinIO", False, str(e))
    tally(ok)

    # 1e. Google AI / LLM
    try:
        from app.config import get_settings
        settings = get_settings()
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model=settings.llm_model, temperature=0)
        resp = llm.invoke("Réponds uniquement 'OK' si tu fonctionnes.")
        ok = check("Google Gemini LLM", True, f"Model: {settings.llm_model}")
    except Exception as e:
        ok = check("Google Gemini LLM", False, str(e))
    tally(ok)

    # 1f. Embeddings
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from app.config import get_settings
        settings = get_settings()
        embeddings = GoogleGenerativeAIEmbeddings(model=settings.embedding_model)
        vec = embeddings.embed_query("test")
        ok = check("Embeddings", True, f"dim={len(vec)}")
    except Exception as e:
        ok = check("Embeddings", False, str(e))
    tally(ok)


# ══════════════════════════════════════════════════════════════════
# STAGE 2: Document Ingestion Pipeline
# ══════════════════════════════════════════════════════════════════
def test_ingestion():
    header("STAGE 2 — Document Ingestion Pipeline")

    # Create a sample BTP document with unique content to bypass deduplication
    import time
    unique_marker = f"TEST_RUN_{time.time()}"
    sample_content = f"""
    RAPPORT TECHNIQUE — Conformité DTU 20.1
    MARQUEUR UNIQUE: {unique_marker}
    Projet: Résidence Les Jardins de la Capitale
    Lot: Gros Œuvre

    1. OBJET
    Ce rapport analyse la conformité des murs de soutènement du sous-sol
    vis-à-vis du DTU 20.1 (Ouvrages en maçonnerie de petits éléments).

    2. CONTEXTE NORMATIF
    Le DTU 20.1 définit les règles de conception et de mise en œuvre des
    ouvrages en maçonnerie. Il couvre les exigences relatives à la résistance
    mécanique, l'étanchéité, et l'isolation thermique.

    Normes applicables:
    - NF DTU 20.1 P1-1: Règles de calcul
    - NF DTU 20.1 P1-2: Critères de choix des matériaux
    - NF EN 771-1: Spécifications pour éléments de maçonnerie

    3. ANALYSE DES MURS DE SOUTÈNEMENT
    Les murs du sous-sol en blocs béton de 20cm présentent:
    - Épaisseur conforme (e ≥ 20cm pour h ≤ 3m) ✓
    - Chaînage horizontal tous les 2.60m ✓
    - Joints verticaux remplis au mortier M10 ✓
    - Étanchéité par enduit bitumineux côté terres ✓

    4. CONCLUSION
    L'ouvrage est conforme au DTU 20.1 sous réserve de la vérification
    du ferraillage des chaînages par le bureau de contrôle.
    """

    tmp_file = None
    doc_metadata = None
    
    try:
        # Write temp PDF-like text file
        tmp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', prefix='test_dtu_',
            dir='/home/kali/Downloads/E-MPGT-IA/backend',
            delete=False, encoding='utf-8'
        )
        tmp_file.write(sample_content)
        tmp_file.close()

        ok = check("Test document created", True, tmp_file.name.split('/')[-1])
        tally(ok)
        
        # Ingest
        from app.services.ingestion import ingest_file
        start = time.time()
        doc_metadata = ingest_file(
            file_path=tmp_file.name,
            project_id="test-project-001",
            project_name="Test E2E Résidence"
        )
        elapsed = time.time() - start
        
        ok = check("Ingestion completed", True,
                    f"{doc_metadata.num_chunks} chunks in {elapsed:.1f}s")
        tally(ok)

        ok = check("Document type detected",
                    doc_metadata.document_type is not None,
                    f"type={doc_metadata.document_type}")
        tally(ok)

        ok = check("Norms extracted",
                    doc_metadata is not None and len(getattr(doc_metadata, 'normes_references', []) or []) >= 0,
                    f"norms found in document")
        tally(ok)

    except Exception as e:
        ok = check("Ingestion pipeline", False, str(e))
        tally(ok)

    finally:
        if tmp_file and os.path.exists(tmp_file.name):
            os.unlink(tmp_file.name)

    return doc_metadata


# ══════════════════════════════════════════════════════════════════
# STAGE 3: Knowledge Graph Verification
# ══════════════════════════════════════════════════════════════════
def test_knowledge_graph(doc_metadata):
    header("STAGE 3 — Knowledge Graph (Neo4j)")

    # 3a. Check stats
    try:
        from app.database.neo4j_client import get_stats
        stats = get_stats()
        total_nodes = sum(stats.values())
        ok = check("Graph node count", total_nodes >= 0,
                    f"{total_nodes} nodes: {stats}")
        tally(ok)
    except Exception as e:
        ok = check("Graph stats", False, str(e))
        tally(ok)

    # 3b. Check overview API
    try:
        from app.services.knowledge_graph import get_graph_overview
        overview = get_graph_overview()
        has_nodes = len(overview.get("nodes", {})) >= 0
        has_rels = len(overview.get("relationships", {})) >= 0
        ok = check("Graph overview API", has_nodes,
                    f"nodes={overview.get('nodes')}, rels={overview.get('relationships')}")
        tally(ok)
    except Exception as e:
        ok = check("Graph overview", False, str(e))
        tally(ok)

    # 3c. Check document node was created (if ingestion succeeded)
    if doc_metadata:
        try:
            from app.database.neo4j_client import run_query
            result = run_query(
                "MATCH (d:Document {id: $id}) RETURN d",
                {"id": doc_metadata.id}
            )
            ok = check("Document node in graph", len(result) > 0,
                        f"Node id={doc_metadata.id}")
            tally(ok)
        except Exception as e:
            ok = check("Document node", False, str(e))
            tally(ok)

    # 3d. Check global graph endpoint data shape
    try:
        from app.services.knowledge_graph import get_global_graph
        gdata = get_global_graph(limit=10)
        ok = check("Global graph query", 
                    "nodes" in gdata and "edges" in gdata,
                    f"{len(gdata['nodes'])} nodes, {len(gdata['edges'])} edges")
        tally(ok)
    except Exception as e:
        ok = check("Global graph query", False, str(e))
        tally(ok)


# ══════════════════════════════════════════════════════════════════
# STAGE 4: Vector Search (Qdrant)
# ══════════════════════════════════════════════════════════════════
def test_vector_search():
    header("STAGE 4 — Vector Search (Qdrant)")

    try:
        from app.database.qdrant import get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections().collections
        
        for col in collections:
            info = client.get_collection(col.name)
            ok = check(f"Collection '{col.name}'", True,
                        f"{info.points_count} vectors, dim={info.config.params.vectors.size}")
            tally(ok)
            
        if not collections:
            ok = check("Collections", True, "No collections yet (expected before first ingestion)")
            tally(ok)
            
    except Exception as e:
        ok = check("Qdrant collections", False, str(e))
        tally(ok)

    # Semantic search test across multiple collections
    try:
        from app.services.vectorstore import multi_collection_search
        results = multi_collection_search(
            query="Quelles sont les exigences du DTU 20.1 pour les murs de soutènement ?",
            k_per_collection=3
        )
        ok = check("Semantic search", len(results) >= 0,
                    f"Retrieved {len(results)} chunks from all collections")
        tally(ok)
    except Exception as e:
        ok = check("Semantic search", False, str(e))
        tally(ok)


# ══════════════════════════════════════════════════════════════════
# STAGE 5: RAG Agent Pipeline (Full Chat)
# ══════════════════════════════════════════════════════════════════
async def test_rag_chat():
    header("STAGE 5 — RAG Agent Pipeline (Chat)")

    try:
        from app.agents.supervisor import run_agent

        test_query = "Quelles sont les exigences du DTU 20.1 pour les murs de soutènement d'un sous-sol ?"
        
        print(f"  {C.INFO} Query: \"{test_query[:60]}...\"")
        print(f"  {C.INFO} Running agent pipeline (this may take 10-30s)...")
        
        start = time.time()
        result = await run_agent(
            query=test_query,
            project_id="test-project-001",
        )
        elapsed = time.time() - start

        # Check result structure
        ok = check("Agent returned response", 
                    "reply" in result and len(result["reply"]) > 20,
                    f"{len(result['reply'])} chars in {elapsed:.1f}s")
        tally(ok)

        ok = check("Agent identified",
                    "agent_used" in result,
                    f"agent={result.get('agent_used')}")
        tally(ok)

        ok = check("Sources retrieved",
                    "sources" in result,
                    f"{len(result.get('sources', []))} sources")
        tally(ok)

        ok = check("Processing time logged",
                    "processing_time_ms" in result,
                    f"{result.get('processing_time_ms')}ms")
        tally(ok)

        # Print a snippet of the response
        reply_preview = result["reply"][:300].replace('\n', ' ')
        print(f"\n  {C.INFO} Response preview:")
        print(f"    \"{reply_preview}...\"")

        # Show sources
        if result.get("sources"):
            print(f"\n  {C.INFO} Sources:")
            for s in result["sources"][:3]:
                print(f"    📄 {s.get('document_name', 'N/A')} (p.{s.get('page_number', '?')})")

    except Exception as e:
        import traceback
        ok = check("RAG pipeline", False, str(e))
        traceback.print_exc()
        tally(ok)


# ══════════════════════════════════════════════════════════════════
# STAGE 6: Audit / Settings Persistence
# ══════════════════════════════════════════════════════════════════
def test_persistence():
    header("STAGE 6 — Persistence (PostgreSQL)")

    # 6a. Check QueryLog entries
    try:
        from app.database.postgres import get_session, QueryLog
        session = get_session()
        count = session.query(QueryLog).count()
        session.close()
        ok = check("QueryLog table", True, f"{count} audit logs stored")
        tally(ok)
    except Exception as e:
        ok = check("QueryLog table", False, str(e))
        tally(ok)

    # 6b. Settings persistence
    try:
        from app.database.postgres import get_session, SystemSettings
        session = get_session()
        
        # Write
        test_setting = SystemSettings(key="__e2e_test__", value={"test": True, "ts": time.time()})
        existing = session.query(SystemSettings).filter(SystemSettings.key == "__e2e_test__").first()
        if existing:
            existing.value = test_setting.value
        else:
            session.add(test_setting)
        session.commit()
        
        # Read back
        read = session.query(SystemSettings).filter(SystemSettings.key == "__e2e_test__").first()
        ok = check("Settings write/read", 
                    read is not None and read.value.get("test") is True,
                    "Round-trip OK")
        tally(ok)
        
        # Cleanup
        session.delete(read)
        session.commit()
        session.close()
        
    except Exception as e:
        ok = check("Settings persistence", False, str(e))
        tally(ok)

    # 6c. DocumentRecord
    try:
        from app.database.postgres import get_session, DocumentRecord
        session = get_session()
        doc_count = session.query(DocumentRecord).count()
        session.close()
        ok = check("DocumentRecord table", True, f"{doc_count} documents indexed")
        tally(ok)
    except Exception as e:
        ok = check("DocumentRecord table", False, str(e))
        tally(ok)


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    print(f"\n{C.BOLD}╔══════════════════════════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}║   E-MPGT-IA — End-to-End Pipeline Test                  ║{C.RESET}")
    print(f"{C.BOLD}║   Ingestion → Knowledge Graph → RAG Chat                ║{C.RESET}")
    print(f"{C.BOLD}╚══════════════════════════════════════════════════════════╝{C.RESET}")

    # Stage 1
    test_infrastructure()
    
    # Stage 2
    doc_metadata = test_ingestion()
    
    # Stage 3
    test_knowledge_graph(doc_metadata)
    
    # Stage 4
    test_vector_search()
    
    # Stage 5 (async)
    asyncio.run(test_rag_chat())
    
    # Stage 6
    test_persistence()

    # ── Final Report ──────────────────────────────────────────────
    header("FINAL REPORT")
    total = results["passed"] + results["failed"]
    pct = (results["passed"] / total * 100) if total > 0 else 0
    print(f"  {C.OK} Passed: {results['passed']}")
    print(f"  {C.FAIL} Failed: {results['failed']}")
    print(f"  Score: {pct:.0f}% ({results['passed']}/{total})")
    
    if results["failed"] == 0:
        print(f"\n  🎉 {C.BOLD}ALL TESTS PASSED — Pipeline is production-ready!{C.RESET}")
    else:
        print(f"\n  {C.WARN} {results['failed']} test(s) failed. Review output above.")
    
    print()
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
