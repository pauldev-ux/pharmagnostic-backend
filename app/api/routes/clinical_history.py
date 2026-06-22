from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import ROLE_DOCTOR, require_roles
from app.models.user import User
from app.schemas.clinical_history import (
    ClinicalHistoryCreate,
    ClinicalHistoryOut,
    ClinicalHistoryStatusUpdate,
    ClinicalHistoryUpdate,
)
from app.schemas.common import Page
from app.services.clinical_history_service import ClinicalHistoryService

router = APIRouter(tags=["clinical-history"])

# El historial clínico solo lo gestiona y consulta el médico.
only_doctor = require_roles(ROLE_DOCTOR)


@router.get("/patients/{patient_id}/clinical-history", response_model=Page[ClinicalHistoryOut])
def list_history(
    patient_id: int,
    tipo_evento: Optional[str] = Query(default=None),
    activo: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(only_doctor),
):
    service = ClinicalHistoryService(db)
    items, total = service.list_for_patient(
        patient_id, tipo_evento=tipo_evento, activo=activo, page=page, page_size=page_size
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post(
    "/patients/{patient_id}/clinical-history",
    response_model=ClinicalHistoryOut,
    status_code=status.HTTP_201_CREATED,
)
def create_history(
    patient_id: int,
    payload: ClinicalHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    return ClinicalHistoryService(db).create_event(patient_id, payload.model_dump(), current_user)


@router.patch("/clinical-history/{history_id}", response_model=ClinicalHistoryOut)
def update_history(
    history_id: int,
    payload: ClinicalHistoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    return ClinicalHistoryService(db).update_event(
        history_id, payload.model_dump(exclude_unset=True), current_user
    )


@router.patch("/clinical-history/{history_id}/status", response_model=ClinicalHistoryOut)
def change_history_status(
    history_id: int,
    payload: ClinicalHistoryStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    return ClinicalHistoryService(db).change_status(history_id, payload.activo, current_user)
