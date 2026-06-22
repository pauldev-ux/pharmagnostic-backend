from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.health_repository import HealthRepository
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=dict[str, str])
def get_health(db: Session = Depends(get_db)):
    repository = HealthRepository(db)
    service = HealthService(repository)
    return service.get_health_status()
