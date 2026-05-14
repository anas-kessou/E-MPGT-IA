"""
Document Ingestion Pipeline — Multi-format parsing, chunking, and indexing.
Handles: PDF, DOCX, images (OCR), and populates Qdrant + Neo4j + PostgreSQL + MinIO.
"""

import os
import re
import uuid
import hashlib
import structlog
from datetime import datetime

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.config import get_settings
from app.models.document import DocumentMetadata, DocumentType, DocumentStatus, Criticite
from app.services.vectorstore import add_documents
from app.services.knowledge_graph import create_document_node
from app.database.qdrant import COLLECTION_DOCUMENTS, COLLECTION_NORMES
from app.database.postgres import get_session, DocumentRecord
from app.database.minio_client import upload_file

logger = structlog.get_logger()

# Known norm patterns for automatic extraction
NORM_PATTERNS = [
    r"DTU\s*[\d\.]+(?:\s*P\d+)?",
    r"NF\s*(?:EN\s*)?[A-Z]?\s*\d+[\-\.\d]*",
    r"EN\s*\d+[\-\.\d]*",
    r"ISO\s*\d+[\-\.\d]*",
    r"CSTB\s*\d+",
]

# Document type detection keywords
TYPE_KEYWORDS = {
    DocumentType.DTU: ["dtu", "document technique unifié"],
    DocumentType.NORME_NF: ["nf en", "nf p", "norme française"],
    DocumentType.FICHE_TECHNIQUE: ["fiche technique", "fiche produit", "descriptif type"],
    DocumentType.RAPPORT_CHANTIER: ["rapport de chantier", "compte rendu chantier", "cr chantier"],
    DocumentType.PV_REUNION: ["procès-verbal", "pv de réunion", "pv réunion"],
    DocumentType.CCTP: ["cctp", "cahier des clauses techniques"],
    DocumentType.DOE: ["doe", "dossier des ouvrages exécutés"],
}

# Lot detection
LOT_KEYWORDS = {
    "Gros Œuvre": ["gros oeuvre", "gros œuvre", "maçonnerie", "béton", "fondation"],
    "Plâtrerie": ["placo", "plâtrerie", "cloison", "plafond", "doublage"],
    "Étanchéité": ["étanchéité", "étanchéite", "toiture", "terrasse"],
    "Façade": ["façade", "facade", "bardage", "ite", "isolation extérieure"],
    "Plomberie": ["plomberie", "sanitaire", "canalisation", "eau"],
    "Électricité": ["électricité", "electricite", "courant", "câblage"],
    "CVC": ["cvc", "chauffage", "ventilation", "climatisation"],
    "Menuiserie": ["menuiserie", "fenêtre", "porte", "vitrage"],
    "Peinture": ["peinture", "revêtement", "finition"],
}


def ingest_file(
    file_path: str,
    project_id: str | None = None,
    project_name: str | None = None,
    file_data: bytes | None = None,
) -> DocumentMetadata:
    """
    Full ingestion pipeline for a single file:
    1. Parse document → extract text
    2. Detect metadata (type, lot, norms)
    3. Store original in MinIO
    4. Chunk + vectorize in Qdrant
    5. Create KG nodes in Neo4j
    6. Save metadata in PostgreSQL
    """
    settings = get_settings()
    filename = os.path.basename(file_path)
    doc_id = str(uuid.uuid4())

    logger.info("ingestion_start", file=filename, doc_id=doc_id)

    # ── Step 1: Parse document ─────────────────────────────────
    raw_docs = _parse_document(file_path)
    full_text = "\n".join([doc.page_content for doc in raw_docs])
    content_hash = hashlib.sha256(full_text.encode()).hexdigest()

    # Check for duplicate
    session = get_session()
    existing = session.query(DocumentRecord).filter_by(content_hash=content_hash).first()
    if existing:
        logger.info("ingestion_duplicate", file=filename, existing_id=existing.id)
        session.close()
        return DocumentMetadata(
            id=existing.id,
            filename=filename,
            status=DocumentStatus.INDEXED,
            content_hash=content_hash,
        )

    # ── Step 2: Detect metadata ────────────────────────────────
    doc_type = _detect_document_type(filename, full_text)
    detected_lot = _detect_lot(filename, full_text)
    normes = _extract_norms(full_text)
    criticite = _assess_criticality(doc_type, normes)

    metadata = DocumentMetadata(
        id=doc_id,
        filename=filename,
        document_type=doc_type,
        project_id=project_id,
        project_name=project_name,
        lot=detected_lot,
        date_indexed=datetime.utcnow(),
        criticite=criticite,
        status=DocumentStatus.PROCESSING,
        num_pages=len(raw_docs),
        file_size_bytes=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        normes_references=normes,
        content_hash=content_hash,
    )

    # ── Step 3: Store original in MinIO ────────────────────────
    try:
        if file_data is None and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_data = f.read()
        if file_data:
            minio_path = upload_file(
                file_data,
                f"documents/{project_id or 'general'}/{doc_id}/{filename}",
            )
            metadata.minio_path = minio_path
    except Exception as e:
        logger.warning("minio_upload_skip", error=str(e))

    # ── Step 4: Chunk + vectorize in Qdrant ────────────────────
    # Configuration High-Resolution : 2200-2800 caractères + overlap 450
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2500,
        chunk_overlap=450,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = text_splitter.split_documents(raw_docs)

    # Enrich chaque chunk avec des métadonnées riches
    enriched_chunks = []
    for i, chunk in enumerate(chunks):
        # Extraction du titre de section (première ligne significative)
        lines = [l for l in chunk.page_content.split('\n') if len(l.strip()) > 5]
        section_title = lines[0][:120] if lines else "Section indéterminée"
        
        # PyPDFLoader uses 0-indexed "page" key → convert to 1-indexed
        raw_page = chunk.metadata.get("page")
        page_number = (raw_page + 1) if raw_page is not None else None
        
        chunk.metadata.update({
            "doc_id": doc_id,
            "document_name": filename,
            "filename": filename,
            "page_number": page_number,
            "section_title": section_title,
            "document_type": doc_type.value,
            "type": doc_type.value,
            "project_id": project_id or "",
            "lot": detected_lot or "Général",
            "chunk_index": i,
            "total_chunks": len(chunks),
            "normes": ",".join(normes),
            "criticite": criticite.value,
        })
        enriched_chunks.append(chunk)

    # Choose collection based on document type
    collection = COLLECTION_NORMES if doc_type in (DocumentType.DTU, DocumentType.NORME_NF) else COLLECTION_DOCUMENTS
    try:
        add_documents(enriched_chunks, collection_name=collection)
        metadata.num_chunks = len(enriched_chunks)
    except Exception as e:
        logger.error("qdrant_indexing_error", error=str(e))
        metadata.status = DocumentStatus.ERROR

    # ── Step 5: Create KG nodes in Neo4j ───────────────────────
    try:
        create_document_node(doc_id, metadata.model_dump())
    except Exception as e:
        logger.warning("neo4j_node_skip", error=str(e))

    # ── Step 6: Save metadata in PostgreSQL ────────────────────
    try:
        record = DocumentRecord(
            id=doc_id,
            filename=filename,
            document_type=doc_type.value,
            project_id=project_id,
            project_name=project_name,
            lot=detected_lot,
            date_indexed=datetime.utcnow(),
            criticite=criticite.value,
            status=metadata.status.value if hasattr(metadata.status, 'value') else str(metadata.status),
            num_pages=len(raw_docs),
            num_chunks=len(enriched_chunks),
            file_size_bytes=metadata.file_size_bytes,
            minio_path=metadata.minio_path,
            normes_references=normes,
            content_hash=content_hash,
        )
        session.add(record)
        session.commit()
        metadata.status = DocumentStatus.INDEXED
    except Exception as e:
        logger.error("postgres_save_error", error=str(e))
        session.rollback()
        metadata.status = DocumentStatus.ERROR
    finally:
        session.close()

    logger.info(
        "ingestion_complete",
        doc_id=doc_id,
        chunks=len(enriched_chunks),
        type=doc_type.value,
        norms=len(normes),
    )
    return metadata


def ingest_directory(
    directory: str,
    project_id: str | None = None,
    project_name: str | None = None,
) -> list[DocumentMetadata]:
    """Ingest all supported files in a directory recursively."""
    results = []
    supported_extensions = {".pdf", ".docx", ".doc", ".txt", ".xlsx"}

    for root, _dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in supported_extensions):
                file_path = os.path.join(root, file)
                try:
                    metadata = ingest_file(file_path, project_id, project_name)
                    results.append(metadata)
                except Exception as e:
                    logger.error("ingest_file_error", file=file, error=str(e))

    logger.info("directory_ingestion_complete", directory=directory, files=len(results))
    return results


# ── Private helpers ────────────────────────────────────────────────

def _parse_document(file_path: str) -> list[Document]:
    """Parse a document into LangChain Documents."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
        return loader.load()
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": file_path})]
    else:
        # Fallback: try to read as text
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return [Document(page_content=content, metadata={"source": file_path})]
        except Exception:
            logger.warning("parse_unsupported", file=file_path, ext=ext)
            return []


def _detect_document_type(filename: str, text: str) -> DocumentType:
    """Auto-detect document type from filename and content."""
    combined = (filename + " " + text[:2000]).lower()
    for doc_type, keywords in TYPE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return doc_type
    return DocumentType.AUTRE


def _detect_lot(filename: str, text: str) -> str | None:
    """Auto-detect construction lot from filename and content."""
    combined = (filename + " " + text[:3000]).lower()
    for lot_name, keywords in LOT_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return lot_name
    return None


def _extract_norms(text: str) -> list[str]:
    """Extract all norm references (DTU, NF, EN, ISO) from text."""
    norms = set()
    for pattern in NORM_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            norms.add(match.strip().upper())
    return sorted(list(norms))


def _assess_criticality(doc_type: DocumentType, norms: list[str]) -> Criticite:
    """Assess document criticality based on type and norm references."""
    if doc_type in (DocumentType.DTU, DocumentType.NORME_NF):
        return Criticite.HAUTE
    if len(norms) > 3:
        return Criticite.HAUTE
    if len(norms) > 0:
        return Criticite.MOYENNE
    return Criticite.BASSE
