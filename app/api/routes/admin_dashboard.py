from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACIST, require_admin, require_roles
from app.models.user import User
from app.schemas.dashboard import RecipeTimeline
from app.services.dashboard_service import DashboardService

router = APIRouter(tags=["admin-dashboard"])


def _rango(
    fecha_inicio: Optional[datetime] = Query(default=None),
    fecha_fin: Optional[datetime] = Query(default=None),
) -> tuple[Optional[datetime], Optional[datetime]]:
    return fecha_inicio, fecha_fin


@router.get("/admin/dashboard/summary", response_model=dict)
def summary(rango=Depends(_rango), db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return DashboardService(db).summary(*rango)


@router.get("/admin/dashboard/recipes", response_model=dict)
def recipes(rango=Depends(_rango), db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return DashboardService(db).recipes(*rango)


@router.get("/admin/dashboard/alerts", response_model=dict)
def alerts(rango=Depends(_rango), db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return DashboardService(db).alerts(*rango)


@router.get("/admin/dashboard/validations", response_model=dict)
def validations(rango=Depends(_rango), db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return DashboardService(db).validations(*rango)


@router.get("/admin/dashboard/medications", response_model=dict)
def medications(rango=Depends(_rango), db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return DashboardService(db).medications(*rango)


# La línea de tiempo de la receta puede consultarla el personal clínico/farmacia.
@router.get("/prescriptions/{recipe_id}/timeline", response_model=RecipeTimeline)
def recipe_timeline(
    recipe_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACIST)),
):
    return DashboardService(db).recipe_timeline(recipe_id)
