from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import get_db
from app.repositories.health_repository import HealthRepository
from app.services import auditoria_service
from app.services.health_service import HealthService

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    debug=settings.APP_DEBUG,
)

origins = [origin.strip() for origin in settings.FRONTEND_URL.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import logging
import time

_perf_logger = logging.getLogger("pharmagnostic.perf")


@app.middleware("http")
async def capturar_ip(request: Request, call_next):
    # Guarda la IP de origen para que la auditoría la registre sin acoplar servicios,
    # y mide el tiempo de respuesta del endpoint (sin exponer datos sensibles).
    auditoria_service.set_current_ip(request.client.host if request.client else None)
    inicio = time.perf_counter()
    response = await call_next(request)
    duracion_ms = int((time.perf_counter() - inicio) * 1000)
    response.headers["X-Process-Time-ms"] = str(duracion_ms)
    if duracion_ms >= 300:  # solo registra los lentos para no llenar el log
        _perf_logger.info("%s %s -> %s (%d ms)", request.method, request.url.path, response.status_code, duracion_ms)
    return response


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
