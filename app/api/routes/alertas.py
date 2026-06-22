from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import ROLE_ADMIN, ROLE_DOCTOR, require_roles
from app.models.user import User
from app.schemas.alerta import AlertaOut, AlertaReviewUpdate, PrevalidationResult
from app.services.alerta_service import AlertaService

router = APIRouter(tags=["alertas-clinicas"])

can_read = require_roles(ROLE_ADMIN, ROLE_DOCTOR)
only_doctor = require_roles(ROLE_DOCTOR)


@router.post("/prescriptions/{prescription_id}/prevalidate", response_model=PrevalidationResult)
def prevalidate(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    return AlertaService(db).prevalidate(prescription_id, current_user)


@router.get("/prescriptions/{prescription_id}/alerts", response_model=list[AlertaOut])
def list_alerts(
    prescription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    return AlertaService(db).list_for_recipe(prescription_id)


@router.patch("/alerts/{alert_id}/review", response_model=AlertaOut)
def review_alert(
    alert_id: int,
    payload: AlertaReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    return AlertaService(db).review(alert_id, payload.revisada, current_user)
