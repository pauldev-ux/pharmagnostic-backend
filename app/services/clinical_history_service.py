from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.clinical_history import ClinicalHistory
from app.models.user import User
from app.repositories.clinical_history_repository import ClinicalHistoryRepository
from app.repositories.patient_repository import PatientRepository
from app.services.audit_service import log_action


class ClinicalHistoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ClinicalHistoryRepository(db)
        self.patient_repository = PatientRepository(db)

    def _get_patient_or_404(self, patient_id: int):
        patient = self.patient_repository.get_by_id(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        return patient

    def list_for_patient(
        self,
        patient_id: int,
        tipo_evento: str | None = None,
        activo: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ClinicalHistory], int]:
        self._get_patient_or_404(patient_id)
        skip = (page - 1) * page_size
        return self.repository.get_all_by_patient(
            patient_id, tipo_evento=tipo_evento, activo=activo, skip=skip, limit=page_size
        )

    def get_event(self, history_id: int) -> ClinicalHistory:
        event = self.repository.get_by_id(history_id)
        if not event:
            raise HTTPException(status_code=404, detail="Evento clínico no encontrado")
        return event

    def create_event(self, patient_id: int, data: dict, current_user: User) -> ClinicalHistory:
        patient = self._get_patient_or_404(patient_id)
        if not patient.activo:
            raise HTTPException(
                status_code=400,
                detail="No se pueden registrar eventos en un paciente inactivo",
            )
        event = ClinicalHistory(
            id_paciente=patient_id,
            id_usuario=current_user.id_usuario,
            tipo_evento=data["tipo_evento"].strip(),
            descripcion=data["descripcion"],
            fecha_evento=data.get("fecha_evento") or datetime.utcnow(),
            activo=True,
        )
        self.db.add(event)
        self.db.flush()
        log_action(self.db, current_user, "crear", "historial", event.id_historial)
        self.db.commit()
        self.db.refresh(event)
        return event

    def update_event(self, history_id: int, data: dict, current_user: User) -> ClinicalHistory:
        event = self.get_event(history_id)
        for field in ("tipo_evento", "descripcion", "fecha_evento"):
            if field in data and data[field] is not None:
                setattr(event, field, data[field])
        log_action(self.db, current_user, "actualizar", "historial", event.id_historial)
        return self.repository.update(event)

    def change_status(self, history_id: int, activo: bool, current_user: User) -> ClinicalHistory:
        event = self.get_event(history_id)
        event.activo = activo
        accion = "activar" if activo else "desactivar"
        log_action(self.db, current_user, accion, "historial", event.id_historial)
        return self.repository.update(event)
