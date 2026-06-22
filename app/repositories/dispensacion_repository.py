from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.dispensacion import Dispensacion
from app.models.prescription import Prescription


class DispensacionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, dispensacion_id: int) -> Optional[Dispensacion]:
        return (
            self.db.query(Dispensacion)
            .filter(Dispensacion.id_dispensacion == dispensacion_id)
            .first()
        )

    def get_by_codigo(self, codigo: str) -> Optional[Dispensacion]:
        return (
            self.db.query(Dispensacion)
            .filter(Dispensacion.codigo_verificacion == codigo)
            .first()
        )

    def get_pending_for_recipe(self, recipe_id: int) -> Optional[Dispensacion]:
        return (
            self.db.query(Dispensacion)
            .filter(Dispensacion.id_receta == recipe_id, Dispensacion.estado == "pendiente")
            .order_by(Dispensacion.id_dispensacion.desc())
            .first()
        )

    def get_latest_for_recipe(self, recipe_id: int) -> Optional[Dispensacion]:
        return (
            self.db.query(Dispensacion)
            .filter(Dispensacion.id_receta == recipe_id)
            .order_by(Dispensacion.id_dispensacion.desc())
            .first()
        )

    def list_all(self, estado: Optional[str] = None) -> list[Dispensacion]:
        query = self.db.query(Dispensacion).options(
            joinedload(Dispensacion.receta).joinedload(Prescription.paciente),
            joinedload(Dispensacion.receta).joinedload(Prescription.medico),
        )
        if estado:
            query = query.filter(Dispensacion.estado == estado)
        return query.order_by(Dispensacion.id_dispensacion.desc()).all()

    def create(self, dispensacion: Dispensacion) -> Dispensacion:
        self.db.add(dispensacion)
        self.db.commit()
        self.db.refresh(dispensacion)
        return dispensacion

    def save(self, dispensacion: Dispensacion) -> Dispensacion:
        self.db.commit()
        self.db.refresh(dispensacion)
        return dispensacion
