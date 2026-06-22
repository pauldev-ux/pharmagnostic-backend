from typing import Optional

from sqlalchemy.orm import Session

from app.models.clinical_history import ClinicalHistory


class ClinicalHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, history_id: int) -> Optional[ClinicalHistory]:
        return (
            self.db.query(ClinicalHistory)
            .filter(ClinicalHistory.id_historial == history_id)
            .first()
        )

    def get_all_by_patient(
        self,
        patient_id: int,
        tipo_evento: Optional[str] = None,
        activo: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ClinicalHistory], int]:
        query = self.db.query(ClinicalHistory).filter(ClinicalHistory.id_paciente == patient_id)

        if tipo_evento:
            query = query.filter(ClinicalHistory.tipo_evento == tipo_evento)
        if activo is not None:
            query = query.filter(ClinicalHistory.activo.is_(activo))

        total = query.count()
        items = (
            query.order_by(ClinicalHistory.fecha_evento.desc(), ClinicalHistory.id_historial.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def create(self, history: ClinicalHistory) -> ClinicalHistory:
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def update(self, history: ClinicalHistory) -> ClinicalHistory:
        self.db.commit()
        self.db.refresh(history)
        return history
