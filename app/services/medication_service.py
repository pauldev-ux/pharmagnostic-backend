from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.medication import Medication
from app.models.user import User
from app.repositories.medication_repository import MedicationRepository
from app.services.audit_service import log_action


class MedicationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = MedicationRepository(db)

    def list_medications(
        self,
        search: str | None = None,
        estado: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Medication], int]:
        skip = (page - 1) * page_size
        return self.repository.get_all(search=search, estado=estado, skip=skip, limit=page_size)

    def get_medication(self, medication_id: int) -> Medication:
        medication = self.repository.get_by_id(medication_id)
        if not medication:
            raise HTTPException(status_code=404, detail="Medicamento no encontrado")
        return medication

    def create_medication(self, data: dict, current_user: User) -> Medication:
        medication = Medication(
            nombre=data["nombre"],
            descripcion=data.get("descripcion"),
            dosis=data.get("dosis"),
            presentacion=data.get("presentacion"),
            precio=data.get("precio"),
            estado="active",
            id_usuario_creacion=current_user.id_usuario,
        )
        self.db.add(medication)
        self.db.flush()
        log_action(self.db, current_user, "crear", "medicamento", medication.id_medicamento)
        self.db.commit()
        self.db.refresh(medication)
        return medication

    def update_medication(self, medication_id: int, data: dict, current_user: User) -> Medication:
        medication = self.get_medication(medication_id)
        for field in ("nombre", "descripcion", "dosis", "presentacion", "precio"):
            if field in data and data[field] is not None:
                setattr(medication, field, data[field])
        log_action(self.db, current_user, "actualizar", "medicamento", medication.id_medicamento)
        return self.repository.update(medication)

    def change_status(self, medication_id: int, estado: str, current_user: User) -> Medication:
        medication = self.get_medication(medication_id)
        medication.estado = estado
        log_action(self.db, current_user, f"estado:{estado}", "medicamento", medication.id_medicamento)
        return self.repository.update(medication)
