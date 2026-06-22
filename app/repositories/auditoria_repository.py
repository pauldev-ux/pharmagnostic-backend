from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.auditoria import Auditoria


class AuditoriaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, audit_id: int) -> Optional[Auditoria]:
        return (
            self.db.query(Auditoria)
            .options(joinedload(Auditoria.usuario))
            .filter(Auditoria.id_auditoria == audit_id)
            .first()
        )

    def _filtered_query(
        self,
        id_usuario: Optional[int],
        accion: Optional[str],
        modulo: Optional[str],
        tabla_afectada: Optional[str],
        fecha_inicio: Optional[datetime],
        fecha_fin: Optional[datetime],
    ):
        query = self.db.query(Auditoria)
        if id_usuario is not None:
            query = query.filter(Auditoria.id_usuario == id_usuario)
        if accion:
            query = query.filter(Auditoria.accion == accion)
        if modulo:
            query = query.filter(Auditoria.modulo == modulo)
        if tabla_afectada:
            query = query.filter(Auditoria.tabla_afectada == tabla_afectada)
        if fecha_inicio:
            query = query.filter(Auditoria.fecha_accion >= fecha_inicio)
        if fecha_fin:
            query = query.filter(Auditoria.fecha_accion <= fecha_fin)
        return query

    def list(
        self,
        id_usuario: Optional[int] = None,
        accion: Optional[str] = None,
        modulo: Optional[str] = None,
        tabla_afectada: Optional[str] = None,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Auditoria], int]:
        base = self._filtered_query(id_usuario, accion, modulo, tabla_afectada, fecha_inicio, fecha_fin)
        total = base.with_entities(Auditoria.id_auditoria).count()
        items = (
            base.options(joinedload(Auditoria.usuario))
            .order_by(Auditoria.id_auditoria.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def distinct_actions(self) -> list[str]:
        rows = self.db.query(Auditoria.accion).distinct().order_by(Auditoria.accion).all()
        return [r[0] for r in rows]

    def distinct_modules(self) -> list[str]:
        rows = self.db.query(Auditoria.modulo).distinct().order_by(Auditoria.modulo).all()
        return [r[0] for r in rows]
