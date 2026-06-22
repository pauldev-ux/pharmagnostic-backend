from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.diagnosis import Diagnosis


class DiagnosisRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, diagnosis_id: int) -> Optional[Diagnosis]:
        return self.db.query(Diagnosis).filter(Diagnosis.id_diagnostico == diagnosis_id).first()

    def get_all_by_patient(
        self,
        patient_id: int,
        search: Optional[str] = None,
        tipo: Optional[str] = None,
        activo: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Diagnosis], int]:
        query = self.db.query(Diagnosis).filter(Diagnosis.id_paciente == patient_id)

        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Diagnosis.descripcion.ilike(term),
                    Diagnosis.codigo_cie10.ilike(term),
                )
            )
        if tipo:
            query = query.filter(Diagnosis.tipo == tipo)
        if activo is not None:
            query = query.filter(Diagnosis.activo.is_(activo))

        total = query.count()
        items = (
            query.order_by(Diagnosis.fecha_diagnostico.desc(), Diagnosis.id_diagnostico.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def create(self, diagnosis: Diagnosis) -> Diagnosis:
        self.db.add(diagnosis)
        self.db.commit()
        self.db.refresh(diagnosis)
        return diagnosis

    def update(self, diagnosis: Diagnosis) -> Diagnosis:
        diagnosis.fecha_actualizacion = datetime.utcnow()
        self.db.commit()
        self.db.refresh(diagnosis)
        return diagnosis
