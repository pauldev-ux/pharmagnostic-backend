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
from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionOut,
    PrescriptionStatusUpdate,
    PrescriptionUpdate,
)
from app.services.prescription_service import PrescriptionService

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

can_read = require_roles(ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACIST)
can_write = require_roles(ROLE_ADMIN, ROLE_DOCTOR)
can_change_status = require_roles(ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACIST)


@router.get("", response_model=Page[PrescriptionOut])
def list_prescriptions(
    patient_id: Optional[int] = Query(default=None),
    estado: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    service = PrescriptionService(db)
    items, total = service.list_prescriptions(
        patient_id=patient_id, estado=estado, page=page, page_size=page_size
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{prescription_id}", response_model=PrescriptionOut)
def get_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    return PrescriptionService(db).get_prescription(prescription_id)


@router.post("", response_model=PrescriptionOut, status_code=status.HTTP_201_CREATED)
def create_prescription(
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return PrescriptionService(db).create_prescription(payload.model_dump(), current_user)


@router.patch("/{prescription_id}", response_model=PrescriptionOut)
def update_prescription(
    prescription_id: int,
    payload: PrescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_write),
):
    return PrescriptionService(db).update_prescription(
        prescription_id, payload.model_dump(exclude_unset=True), current_user
    )


@router.patch("/{prescription_id}/status", response_model=PrescriptionOut)
def change_status(
    prescription_id: int,
    payload: PrescriptionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_change_status),
):
    return PrescriptionService(db).change_status(prescription_id, payload.estado, current_user)
