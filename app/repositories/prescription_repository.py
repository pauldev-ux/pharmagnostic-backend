from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.prescription import Prescription


class PrescriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, prescription_id: int) -> Optional[Prescription]:
        return (
            self.db.query(Prescription)
            .options(
                joinedload(Prescription.items),
                joinedload(Prescription.paciente),
                joinedload(Prescription.medico),
            )
            .filter(Prescription.id_receta == prescription_id)
            .first()
        )

    def get_all(
        self,
        patient_id: Optional[int] = None,
        estado: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Prescription], int]:
        filters = []
        if patient_id is not None:
            filters.append(Prescription.id_paciente == patient_id)
        if estado is not None:
            filters.append(Prescription.estado == estado)

        # Conteo sobre una consulta limpia (sin joinedload de colecciones)
        count_query = self.db.query(Prescription)
        for condition in filters:
            count_query = count_query.filter(condition)
        total = count_query.count()

        query = self.db.query(Prescription).options(
            joinedload(Prescription.items),
            joinedload(Prescription.paciente),
            joinedload(Prescription.medico),
        )
        for condition in filters:
            query = query.filter(condition)

        items = (
            query.order_by(Prescription.id_receta.desc()).offset(skip).limit(limit).all()
        )
        return items, total
