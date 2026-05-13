"""
Resources Router — Manage RAG resource files (list, upload, delete, ingest).
These are the pre-loaded PDF/document files that form the knowledge base.
"""

import os
import uuid
import structlog
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

from app.services.ingestion import ingest_file
from app.database.postgres import get_session, DocumentRecord

logger = structlog.get_logger()

router = APIRouter(prefix="/api/resources", tags=["Resources"])

# Path to the resources directory (relative to backend/)
RESOURCES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources")
os.makedirs(RESOURCES_DIR, exist_ok=True)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".xlsx"}


def _get_file_info(filename: str) -> dict:
    """Get metadata for a single resource file."""
    filepath = os.path.join(RESOURCES_DIR, filename)
    ext = os.path.splitext(filename)[1].lower()
    size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

    # Check if already ingested (by matching filename in DB)
    ingested = False
    try:
        session = get_session()
        record = session.query(DocumentRecord).filter(
            DocumentRecord.filename == filename
        ).first()
        ingested = record is not None
        session.close()
    except Exception:
        pass

    return {
        "filename": filename,
        "size_bytes": size,
        "size_display": _format_size(size),
        "extension": ext,
        "ingested": ingested,
    }


def _format_size(size_bytes: int) -> str:
    """Format file size for display."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


@router.get("/")
async def list_resources():
    """List all resource files in the resources directory."""
    try:
        files = []
        for filename in sorted(os.listdir(RESOURCES_DIR)):
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(_get_file_info(filename))

        return {
            "resources": files,
            "total": len(files),
            "directory": RESOURCES_DIR,
        }
    except Exception as e:
        logger.error("list_resources_error", error=str(e))
        return {"resources": [], "total": 0, "error": str(e)}


@router.post("/upload")
async def upload_resource(file: UploadFile = File(...)):
    """Upload a new file to the resources directory."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non supporté: {ext}. Formats acceptés: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    filepath = os.path.join(RESOURCES_DIR, file.filename)

    try:
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)

        logger.info("resource_uploaded", filename=file.filename, size=len(content))
        return {
            "message": f"Fichier '{file.filename}' ajouté aux ressources",
            "file": _get_file_info(file.filename),
        }
    except Exception as e:
        logger.error("resource_upload_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{filename}")
async def delete_resource(filename: str):
    """Delete a resource file from the resources directory."""
    filepath = os.path.join(RESOURCES_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Fichier non trouvé")

    # Security: prevent path traversal
    if os.path.dirname(os.path.abspath(filepath)) != os.path.abspath(RESOURCES_DIR):
        raise HTTPException(status_code=400, detail="Chemin invalide")

    try:
        os.remove(filepath)
        logger.info("resource_deleted", filename=filename)
        return {"message": f"Fichier '{filename}' supprimé"}
    except Exception as e:
        logger.error("resource_delete_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_all_resources():
    """Ingest all resource files into the RAG pipeline (skips duplicates)."""
    results = []
    for filename in sorted(os.listdir(RESOURCES_DIR)):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        filepath = os.path.join(RESOURCES_DIR, filename)
        try:
            with open(filepath, "rb") as f:
                file_data = f.read()

            metadata = ingest_file(
                file_path=filepath,
                project_id=None,
                project_name=None,
                file_data=file_data,
            )
            results.append({
                "filename": filename,
                "status": metadata.status.value if hasattr(metadata.status, 'value') else str(metadata.status),
                "chunks": metadata.num_chunks,
                "id": metadata.id,
            })
        except Exception as e:
            logger.error("resource_ingest_error", filename=filename, error=str(e))
            results.append({
                "filename": filename,
                "status": "error",
                "error": str(e),
            })

    ingested = sum(1 for r in results if r.get("status") == "indexed")
    skipped = sum(1 for r in results if r.get("status") != "error" and r.get("status") != "indexed")

    return {
        "message": f"{ingested} fichiers ingérés, {skipped} déjà indexés",
        "results": results,
        "total": len(results),
    }


@router.post("/ingest/{filename}")
async def ingest_single_resource(filename: str):
    """Ingest a single resource file into the RAG pipeline."""
    filepath = os.path.join(RESOURCES_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Fichier non trouvé")

    # Security: prevent path traversal
    if os.path.dirname(os.path.abspath(filepath)) != os.path.abspath(RESOURCES_DIR):
        raise HTTPException(status_code=400, detail="Chemin invalide")

    try:
        with open(filepath, "rb") as f:
            file_data = f.read()

        metadata = ingest_file(
            file_path=filepath,
            project_id=None,
            project_name=None,
            file_data=file_data,
        )
        return {
            "message": f"Fichier '{filename}' ingéré avec succès",
            "status": metadata.status.value if hasattr(metadata.status, 'value') else str(metadata.status),
            "chunks": metadata.num_chunks,
            "id": metadata.id,
        }
    except Exception as e:
        logger.error("resource_ingest_single_error", filename=filename, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
