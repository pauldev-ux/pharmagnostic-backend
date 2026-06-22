from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.medication import Medication


class MedicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, medication_id: int) -> Optional[Medication]:
        return self.db.query(Medication).filter(Medication.id_medicamento == medication_id).first()

    def get_all(
        self,
        search: Optional[str] = None,
        estado: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Medication], int]:
        query = self.db.query(Medication)

        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Medication.nombre.ilike(term),
                    Medication.descripcion.ilike(term),
                    Medication.presentacion.ilike(term),
                )
            )

        if estado is not None:
            query = query.filter(Medication.estado == estado)

        total = query.count()
        items = query.order_by(Medication.nombre).offset(skip).limit(limit).all()
        return items, total

    def create(self, medication: Medication) -> Medication:
        self.db.add(medication)
        self.db.commit()
        self.db.refresh(medication)
        return medication

    def update(self, medication: Medication) -> Medication:
        medication.fecha_actualizacion = datetime.utcnow()
        self.db.commit()
        self.db.refresh(medication)
        return medication
