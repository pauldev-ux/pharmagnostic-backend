from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import ROLE_ADMIN, ROLE_DOCTOR, require_roles
from app.models.user import User
from app.schemas.common import Page
from app.schemas.patient import (
    PatientCreate,
    PatientOut,
    PatientStatusUpdate,
    PatientUpdate,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["patients"])

# Pacientes: administrador y médico pueden registrar/editar/activar.
# (El historial clínico y los diagnósticos siguen siendo exclusivos del médico.)
can_read = require_roles(ROLE_ADMIN, ROLE_DOCTOR)
can_write = require_roles(ROLE_ADMIN, ROLE_DOCTOR)


@router.get("", response_model=Page[PatientOut])
def list_patients(
    search: Optional[str] = Query(default=None),
    activo: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    service = PatientService(db)
    items, total = service.list_patients(search=search, activo=activo, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    return PatientService(db).get_patient(patient_id)


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return PatientService(db).create_patient(payload.model_dump(), current_user)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return PatientService(db).update_patient(
        patient_id, payload.model_dump(exclude_unset=True), current_user
    )


@router.patch("/{patient_id}/status", response_model=PatientOut)
def change_status(
    patient_id: int,
    payload: PatientStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return PatientService(db).change_status(patient_id, payload.activo, current_user)
