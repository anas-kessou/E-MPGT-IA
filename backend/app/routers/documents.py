"""
Documents Router — Upload, list, and manage BTP documents.
"""

import os
import uuid
import structlog
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional

from app.models.document import (
    DocumentMetadata, DocumentUploadResponse, DocumentListResponse,
    DocumentListItem, DocumentStatus, DocumentType,
)
from app.services.ingestion import ingest_file
from app.database.postgres import get_session, DocumentRecord

logger = structlog.get_logger()

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# Temp dir for uploaded files
UPLOAD_DIR = "/tmp/empgt_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    project_name: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
):
    """Upload and ingest a document into the system."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")

    # Save to temp
    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Run ingestion pipeline
        metadata = ingest_file(
            file_path=temp_path,
            project_id=project_id,
            project_name=project_name,
            file_data=content,
        )

        return DocumentUploadResponse(
            id=metadata.id or str(uuid.uuid4()),
            filename=file.filename,
            status=metadata.status,
            message=f"Document ingéré avec succès: {metadata.num_chunks} chunks, {len(metadata.normes_references)} normes détectées",
            metadata=metadata,
        )

    except Exception as e:
        logger.error("upload_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[str] = None,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
):
    """List all indexed documents with filtering and pagination."""
    session = get_session()
    try:
        query = session.query(DocumentRecord)

        if project_id:
            query = query.filter(DocumentRecord.project_id == project_id)
        if document_type:
            query = query.filter(DocumentRecord.document_type == document_type)
        if status:
            query = query.filter(DocumentRecord.status == status)

        total = query.count()
        records = (
            query.order_by(DocumentRecord.date_indexed.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            DocumentListItem(
                id=r.id,
                filename=r.filename,
                document_type=r.document_type,
                project_name=r.project_name,
                lot=r.lot,
                status=r.status,
                date_indexed=r.date_indexed,
                num_chunks=r.num_chunks or 0,
                criticite=r.criticite or "moyenne",
            )
            for r in records
        ]

        return DocumentListResponse(
            documents=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    finally:
        session.close()


@router.get("/{doc_id}")
async def get_document(doc_id: str):
    """Get a single document's details."""
    session = get_session()
    try:
        record = session.query(DocumentRecord).filter_by(id=doc_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Document non trouvé")

        return {
            "id": record.id,
            "filename": record.filename,
            "document_type": record.document_type,
            "project_id": record.project_id,
            "project_name": record.project_name,
            "lot": record.lot,
            "author": record.author,
            "date_indexed": str(record.date_indexed),
            "criticite": record.criticite,
            "status": record.status,
            "num_pages": record.num_pages,
            "num_chunks": record.num_chunks,
            "file_size_bytes": record.file_size_bytes,
            "normes_references": record.normes_references or [],
            "tags": record.tags or [],
        }
    finally:
        session.close()


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from the system."""
    session = get_session()
    try:
        record = session.query(DocumentRecord).filter_by(id=doc_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Document non trouvé")
        session.delete(record)
        session.commit()
        return {"message": f"Document {doc_id} supprimé"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
