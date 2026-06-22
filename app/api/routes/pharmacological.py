from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACIST, require_roles
from app.models.user import User
from app.schemas.pharmacological import (
    AskRequest,
    AskResponse,
    DocumentoOut,
    DocumentoStatusUpdate,
    FragmentoResultado,
    ProcessResult,
    SearchRequest,
)
from app.services.rag_service import RagService

router = APIRouter(tags=["base-farmacologica"])

# Administrador gestiona; médico y farmacéutico solo consultan. Paciente sin acceso.
only_admin = require_roles(ROLE_ADMIN)
can_consult = require_roles(ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACIST)


@router.post(
    "/pharmacological-documents",
    response_model=DocumentoOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    titulo: Optional[str] = Form(default=None),
    tipo_documento: Optional[str] = Form(default=None),
    fuente: Optional[str] = Form(default=None),
    version: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(only_admin),
):
    return RagService(db).upload_document(file, titulo, tipo_documento, fuente, version)


@router.get("/pharmacological-documents", response_model=list[DocumentoOut])
def list_documents(
    db: Session = Depends(get_db),
    _: User = Depends(can_consult),
):
    return RagService(db).list_documents()


@router.post("/pharmacological-documents/{document_id}/process", response_model=ProcessResult)
def process_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(only_admin),
):
    return RagService(db).process_document(document_id)


@router.patch("/pharmacological-documents/{document_id}/status", response_model=DocumentoOut)
def update_status(
    document_id: int,
    payload: DocumentoStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(only_admin),
):
    service = RagService(db)
    service.set_status(document_id, payload.activo)
    data = service.get_document(document_id).__dict__.copy()
    data["total_fragmentos"] = service.repository.count_fragments(document_id)
    return data


@router.post("/pharmacological-knowledge/search", response_model=list[FragmentoResultado])
def search_knowledge(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    _: User = Depends(can_consult),
):
    return RagService(db).search(payload.query, payload.top_k)


@router.post("/pharmacological-knowledge/ask", response_model=AskResponse)
def ask_knowledge(
    payload: AskRequest,
    db: Session = Depends(get_db),
    _: User = Depends(can_consult),
):
    return RagService(db).ask(payload.query, payload.top_k)
