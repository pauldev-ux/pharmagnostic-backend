from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import ROLE_PATIENT, require_roles
from app.models.user import User
from app.schemas.patient_portal import (
    ChatRequest,
    ChatResponse,
    PortalProfile,
    PortalRecipeDetail,
    PortalRecipeItem,
)
from app.services.patient_portal_service import PatientPortalService

router = APIRouter(prefix="/patient-portal", tags=["patient-portal"])

# Todo el portal está restringido al rol paciente.
only_patient = require_roles(ROLE_PATIENT)


@router.get("/profile", response_model=PortalProfile)
def profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(only_patient),
):
    return PatientPortalService(db).profile(current_user)


@router.get("/recipes", response_model=list[PortalRecipeItem])
def my_recipes(
    db: Session = Depends(get_db),
    current_user: User = Depends(only_patient),
):
    return PatientPortalService(db).list_recipes(current_user)


@router.get("/recipes/{recipe_id}", response_model=PortalRecipeDetail)
def my_recipe_detail(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_patient),
):
    return PatientPortalService(db).get_recipe(recipe_id, current_user)


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_patient),
):
    return PatientPortalService(db).chat(payload.mensaje, current_user)
