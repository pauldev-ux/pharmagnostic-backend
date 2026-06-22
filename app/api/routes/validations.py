from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import ROLE_ADMIN, ROLE_DOCTOR, require_roles
from app.models.user import User
from app.schemas.validacion import JustificarRequest, ValidacionOut, ValidacionResult
from app.services.validation_service import ValidationService

router = APIRouter(tags=["validacion-ia"])

# Validar/justificar: solo médico. Consultar: médico + administrador.
only_doctor = require_roles(ROLE_DOCTOR)
can_read = require_roles(ROLE_ADMIN, ROLE_DOCTOR)


@router.post("/prescriptions/{prescription_id}/validate", response_model=ValidacionResult)
def validate_recipe(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    return ValidationService(db).validate(prescription_id, current_user)


@router.get("/prescriptions/{prescription_id}/validations", response_model=list[ValidacionOut])
def list_validations(
    prescription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    return ValidationService(db).list_for_recipe(prescription_id)


@router.get("/validations/{validation_id}", response_model=ValidacionOut)
def get_validation(
    validation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    return ValidationService(db).get_validation(validation_id)


@router.patch("/prescriptions/{prescription_id}/justify", response_model=dict)
def justify_recipe(
    prescription_id: int,
    payload: JustificarRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    return ValidationService(db).justificar(prescription_id, payload.justificacion, current_user)
