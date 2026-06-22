from typing import Optional

from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem


class PrescriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def _con_relaciones(self, query):
        # selectinload para la colección de ítems (seguro con LIMIT y sin N+1);
        # joinedload para las relaciones many-to-one. Evita el problema de joinedload
        # de colecciones con paginación y elimina las consultas N+1 al serializar.
        return query.options(
            selectinload(Prescription.items).joinedload(PrescriptionItem.medicamento),
            joinedload(Prescription.paciente),
            joinedload(Prescription.medico),
        )

    def get_by_id(self, prescription_id: int) -> Optional[Prescription]:
        return (
            self._con_relaciones(self.db.query(Prescription))
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

        # Conteo sobre una consulta limpia (sin joinedload de colecciones).
        count_query = self.db.query(Prescription)
        for condition in filters:
            count_query = count_query.filter(condition)
        total = count_query.count()

        query = self._con_relaciones(self.db.query(Prescription))
        for condition in filters:
            query = query.filter(condition)

        items = query.order_by(Prescription.id_receta.desc()).offset(skip).limit(limit).all()
        return items, total
