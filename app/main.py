from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import get_db
from app.repositories.health_repository import HealthRepository
from app.services.health_service import HealthService

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    debug=settings.APP_DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/api/health", tags=["health"])
def api_health(db: Session = Depends(get_db)) -> dict:
    """Estado del backend con verificación de PostgreSQL (SELECT 1)."""
    service = HealthService(HealthRepository(db))
    return service.get_health_status()


@app.get("/")
def root() -> dict:
    return {
        "message": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
