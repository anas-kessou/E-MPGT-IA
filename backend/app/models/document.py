"""
Pydantic models for Document management.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    DTU = "dtu"
    NORME_NF = "norme_nf"
    FICHE_TECHNIQUE = "fiche_technique"
    RAPPORT_CHANTIER = "rapport_chantier"
    PV_REUNION = "pv_reunion"
    DEVIS = "devis"
    PLAN = "plan"
    CCTP = "cctp"
    DOE = "doe"
    AUTRE = "autre"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    ERROR = "error"


class Criticite(str, Enum):
    BASSE = "basse"
    MOYENNE = "moyenne"
    HAUTE = "haute"
    CRITIQUE = "critique"


class DocumentMetadata(BaseModel):
    """Rich metadata extracted from / assigned to a document."""
    id: Optional[str] = None
    filename: str
    document_type: DocumentType = DocumentType.AUTRE
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    lot: Optional[str] = None
    author: Optional[str] = None
    date_document: Optional[datetime] = None
    date_indexed: datetime = Field(default_factory=datetime.utcnow)
    criticite: Criticite = Criticite.MOYENNE
    status: DocumentStatus = DocumentStatus.PENDING
    num_pages: int = 0
    num_chunks: int = 0
    file_size_bytes: int = 0
    minio_path: Optional[str] = None
    version: int = 1
    tags: list[str] = []
    normes_references: list[str] = []  # DTU / NF references found
    content_hash: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    id: str
    filename: str
    status: DocumentStatus
    message: str
    metadata: DocumentMetadata


class DocumentListItem(BaseModel):
    """Summary item for document listing."""
    id: str
    filename: str
    document_type: DocumentType
    project_name: Optional[str] = None
    lot: Optional[str] = None
    status: DocumentStatus
    date_indexed: datetime
    num_chunks: int
    criticite: Criticite


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    documents: list[DocumentListItem]
    total: int
    page: int
    page_size: int
