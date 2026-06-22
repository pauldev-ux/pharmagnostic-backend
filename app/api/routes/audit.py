from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_admin
from app.models.user import User
from app.schemas.auditoria import AuditoriaOut
from app.schemas.common import Page
from app.services.auditoria_query_service import AuditoriaQueryService

router = APIRouter(prefix="/audit", tags=["auditoria"])


@router.get("", response_model=Page[AuditoriaOut])
def list_audit(
    usuario: Optional[int] = Query(default=None),
    accion: Optional[str] = Query(default=None),
    modulo: Optional[str] = Query(default=None),
    tabla: Optional[str] = Query(default=None),
    fecha_inicio: Optional[datetime] = Query(default=None),
    fecha_fin: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    service = AuditoriaQueryService(db)
    items, total = service.list(
        id_usuario=usuario,
        accion=accion,
        modulo=modulo,
        tabla_afectada=tabla,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/actions", response_model=list[str])
def audit_actions(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return AuditoriaQueryService(db).actions()


@router.get("/modules", response_model=list[str])
def audit_modules(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return AuditoriaQueryService(db).modules()


@router.get("/{audit_id}", response_model=AuditoriaOut)
def get_audit(audit_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return AuditoriaQueryService(db).get(audit_id)
