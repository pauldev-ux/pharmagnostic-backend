from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import ROLE_ADMIN, ROLE_DOCTOR, require_roles
from app.models.user import User
from app.schemas.common import Page
from app.schemas.diagnosis import (
    DiagnosisCreate,
    DiagnosisOut,
    DiagnosisStatusUpdate,
    DiagnosisUpdate,
)
from app.services.diagnosis_service import DiagnosisService

router = APIRouter(tags=["diagnoses"])

# El administrador consulta diagnósticos; solo el médico los crea o modifica.
can_read = require_roles(ROLE_ADMIN, ROLE_DOCTOR)
can_write = require_roles(ROLE_DOCTOR)


@router.get("/patients/{patient_id}/diagnoses", response_model=Page[DiagnosisOut])
def list_diagnoses(
    patient_id: int,
    search: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    activo: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    service = DiagnosisService(db)
    items, total = service.list_for_patient(
        patient_id, search=search, tipo=tipo, activo=activo, page=page, page_size=page_size
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post(
    "/patients/{patient_id}/diagnoses",
    response_model=DiagnosisOut,
    status_code=status.HTTP_201_CREATED,
)
def create_diagnosis(
    patient_id: int,
    payload: DiagnosisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return DiagnosisService(db).create_diagnosis(patient_id, payload.model_dump(), current_user)


@router.get("/diagnoses/{diagnosis_id}", response_model=DiagnosisOut)
def get_diagnosis(
    diagnosis_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    return DiagnosisService(db).get_diagnosis(diagnosis_id)


@router.patch("/diagnoses/{diagnosis_id}", response_model=DiagnosisOut)
def update_diagnosis(
    diagnosis_id: int,
    payload: DiagnosisUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return DiagnosisService(db).update_diagnosis(
        diagnosis_id, payload.model_dump(exclude_unset=True), current_user
    )


@router.patch("/diagnoses/{diagnosis_id}/status", response_model=DiagnosisOut)
def change_status(
    diagnosis_id: int,
    payload: DiagnosisStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return DiagnosisService(db).change_status(diagnosis_id, payload.activo, current_user)
