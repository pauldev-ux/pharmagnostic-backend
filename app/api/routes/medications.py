from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import (
    ROLE_ADMIN,
    ROLE_DOCTOR,
    ROLE_PHARMACIST,
    require_roles,
)
from app.models.user import User
from app.schemas.common import Page
from app.schemas.medication import (
    MedicationCreate,
    MedicationOut,
    MedicationStatusUpdate,
    MedicationUpdate,
)
from app.services.medication_service import MedicationService

router = APIRouter(prefix="/medications", tags=["medications"])

can_read = require_roles(ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACIST)
can_write = require_roles(ROLE_ADMIN, ROLE_PHARMACIST)


@router.get("", response_model=Page[MedicationOut])
def list_medications(
    search: Optional[str] = Query(default=None),
    estado: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    service = MedicationService(db)
    items, total = service.list_medications(search=search, estado=estado, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{medication_id}", response_model=MedicationOut)
def get_medication(
    medication_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    return MedicationService(db).get_medication(medication_id)


@router.post("", response_model=MedicationOut, status_code=status.HTTP_201_CREATED)
def create_medication(
    payload: MedicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return MedicationService(db).create_medication(payload.model_dump(), current_user)


@router.patch("/{medication_id}", response_model=MedicationOut)
def update_medication(
    medication_id: int,
    payload: MedicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return MedicationService(db).update_medication(
        medication_id, payload.model_dump(exclude_unset=True), current_user
    )


@router.patch("/{medication_id}/status", response_model=MedicationOut)
def change_status(
    medication_id: int,
    payload: MedicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return MedicationService(db).change_status(medication_id, payload.estado, current_user)
