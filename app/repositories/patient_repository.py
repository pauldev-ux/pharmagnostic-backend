from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.patient import Patient


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, patient_id: int) -> Optional[Patient]:
        return self.db.query(Patient).filter(Patient.id_paciente == patient_id).first()

    def get_by_ci(self, ci: str) -> Optional[Patient]:
        return self.db.query(Patient).filter(Patient.ci == ci).first()

    def get_by_user(self, user_id: int) -> Optional[Patient]:
        return self.db.query(Patient).filter(Patient.id_usuario == user_id).first()

    def get_all(
        self,
        search: Optional[str] = None,
        activo: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Patient], int]:
        query = self.db.query(Patient)

        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Patient.nombre.ilike(term),
                    Patient.apellido.ilike(term),
                    Patient.ci.ilike(term),
                )
            )

        if activo is not None:
            query = query.filter(Patient.activo.is_(activo))

        total = query.count()
        items = query.order_by(Patient.id_paciente.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def update(self, patient: Patient) -> Patient:
        patient.fecha_actualizacion = datetime.utcnow()
        self.db.commit()
        self.db.refresh(patient)
        return patient
