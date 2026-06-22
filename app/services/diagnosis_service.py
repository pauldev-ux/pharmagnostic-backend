from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.diagnosis import Diagnosis
from app.models.user import User
from app.repositories.diagnosis_repository import DiagnosisRepository
from app.repositories.patient_repository import PatientRepository
from app.services.audit_service import log_action


class DiagnosisService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = DiagnosisRepository(db)
        self.patient_repository = PatientRepository(db)

    def _get_patient_or_404(self, patient_id: int):
        patient = self.patient_repository.get_by_id(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        return patient

    def list_for_patient(
        self,
        patient_id: int,
        search: str | None = None,
        tipo: str | None = None,
        activo: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Diagnosis], int]:
        self._get_patient_or_404(patient_id)
        skip = (page - 1) * page_size
        return self.repository.get_all_by_patient(
            patient_id, search=search, tipo=tipo, activo=activo, skip=skip, limit=page_size
        )

    def get_diagnosis(self, diagnosis_id: int) -> Diagnosis:
        diagnosis = self.repository.get_by_id(diagnosis_id)
        if not diagnosis:
            raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
        return diagnosis

    @staticmethod
    def _normalize_cie10(value):
        return value.strip().upper() if value else value

    def create_diagnosis(self, patient_id: int, data: dict, current_user: User) -> Diagnosis:
        patient = self._get_patient_or_404(patient_id)
        if not patient.activo:
            raise HTTPException(
                status_code=400,
                detail="No se pueden registrar diagnósticos en un paciente inactivo",
            )

        diagnosis = Diagnosis(
            id_paciente=patient_id,
            id_usuario=current_user.id_usuario,
            codigo_cie10=self._normalize_cie10(data.get("codigo_cie10")),
            descripcion=data["descripcion"],
            tipo=data.get("tipo", "preliminar"),
            observaciones=data.get("observaciones"),
            fecha_diagnostico=data.get("fecha_diagnostico") or datetime.utcnow(),
            activo=True,
        )
        self.db.add(diagnosis)
        self.db.flush()
        log_action(self.db, current_user, "crear", "diagnostico", diagnosis.id_diagnostico)
        self.db.commit()
        self.db.refresh(diagnosis)
        return diagnosis

    def update_diagnosis(self, diagnosis_id: int, data: dict, current_user: User) -> Diagnosis:
        diagnosis = self.get_diagnosis(diagnosis_id)

        if "codigo_cie10" in data and data["codigo_cie10"] is not None:
            diagnosis.codigo_cie10 = self._normalize_cie10(data["codigo_cie10"])
        for field in ("descripcion", "tipo", "observaciones", "fecha_diagnostico"):
            if field in data and data[field] is not None:
                setattr(diagnosis, field, data[field])

        log_action(self.db, current_user, "actualizar", "diagnostico", diagnosis.id_diagnostico)
        return self.repository.update(diagnosis)

    def change_status(self, diagnosis_id: int, activo: bool, current_user: User) -> Diagnosis:
        diagnosis = self.get_diagnosis(diagnosis_id)
        diagnosis.activo = activo
        accion = "activar" if activo else "desactivar"
        log_action(self.db, current_user, accion, "diagnostico", diagnosis.id_diagnostico)
        return self.repository.update(diagnosis)
