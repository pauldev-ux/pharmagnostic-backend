from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.repositories.auditoria_repository import AuditoriaRepository


def _serialize(a: Auditoria) -> dict:
    return {
        "id_auditoria": a.id_auditoria,
        "id_usuario": a.id_usuario,
        "usuario_nombre": (f"{a.usuario.nombre} {a.usuario.apellido}" if a.usuario else None),
        "accion": a.accion,
        "modulo": a.modulo,
        "tabla_afectada": a.tabla_afectada,
        "id_registro": a.id_registro,
        "detalle": a.detalle,
        "ip_origen": a.ip_origen,
        "fecha_accion": a.fecha_accion,
    }


class AuditoriaQueryService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AuditoriaRepository(db)

    def list(
        self,
        id_usuario: Optional[int] = None,
        accion: Optional[str] = None,
        modulo: Optional[str] = None,
        tabla_afectada: Optional[str] = None,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        skip = (page - 1) * page_size
        items, total = self.repository.list(
            id_usuario=id_usuario,
            accion=accion,
            modulo=modulo,
            tabla_afectada=tabla_afectada,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            skip=skip,
            limit=page_size,
        )
        return [_serialize(a) for a in items], total

    def get(self, audit_id: int) -> dict:
        a = self.repository.get_by_id(audit_id)
        if not a:
            raise HTTPException(status_code=404, detail="Registro de auditoría no encontrado")
        return _serialize(a)

    def actions(self) -> list[str]:
        return self.repository.distinct_actions()

    def modules(self) -> list[str]:
        return self.repository.distinct_modules()
