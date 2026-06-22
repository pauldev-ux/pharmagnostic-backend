from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACIST, require_roles
from app.models.user import User
from app.schemas.pharmacy import (
    DispensacionOut,
    DispenseRequest,
    PharmacyRecipeDetail,
    PharmacyRecipeItem,
    QrResponse,
    RejectRequest,
    VerifyQrRequest,
    VerifyQrResponse,
)
from app.services.pharmacy_service import PharmacyService

router = APIRouter(tags=["farmacia"])

# Generar QR = aprobación del médico. Consultar = farmacéutico + médico + admin.
# Dispensar / rechazar = solo farmacéutico.
only_doctor = require_roles(ROLE_DOCTOR)
can_consult = require_roles(ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACIST)
only_pharmacist = require_roles(ROLE_PHARMACIST)


@router.post("/prescriptions/{prescription_id}/generate-qr", response_model=QrResponse)
def generate_qr(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    return PharmacyService(db).generate_qr(prescription_id, current_user)


@router.get("/pharmacy/recipes", response_model=list[PharmacyRecipeItem])
def list_pharmacy_recipes(
    estado: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(can_consult),
):
    return PharmacyService(db).list_recipes(estado=estado, search=search)


@router.get("/pharmacy/recipes/{prescription_id}", response_model=PharmacyRecipeDetail)
def pharmacy_recipe_detail(
    prescription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(can_consult),
):
    return PharmacyService(db).recipe_detail(prescription_id)


@router.post("/pharmacy/verify-qr", response_model=VerifyQrResponse)
def verify_qr(
    payload: VerifyQrRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(can_consult),
):
    return PharmacyService(db).verify_qr(payload.codigo, current_user)


@router.post("/pharmacy/recipes/{prescription_id}/dispense", response_model=DispensacionOut)
def dispense(
    prescription_id: int,
    payload: DispenseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_pharmacist),
):
    return PharmacyService(db).dispense(
        prescription_id, payload.codigo_verificacion, payload.observaciones, current_user
    )


@router.post("/pharmacy/recipes/{prescription_id}/reject", response_model=DispensacionOut)
def reject(
    prescription_id: int,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_pharmacist),
):
    return PharmacyService(db).reject(prescription_id, payload.observaciones, current_user)
