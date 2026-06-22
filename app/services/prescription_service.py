from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.medication import Medication
from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem
from app.models.user import User
from app.repositories.diagnosis_repository import DiagnosisRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.services.audit_service import log_action


class PrescriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PrescriptionRepository(db)
        self.patient_repository = PatientRepository(db)
        self.diagnosis_repository = DiagnosisRepository(db)

    @staticmethod
    def serialize(prescription: Prescription) -> dict:
        return {
            "id_receta": prescription.id_receta,
            "id_paciente": prescription.id_paciente,
            "id_usuario": prescription.id_usuario,
            "id_diagnostico": prescription.id_diagnostico,
            "fecha_emision": prescription.fecha_emision,
            "notas": prescription.notas,
            "estado": prescription.estado,
            "nivel_riesgo": prescription.nivel_riesgo,
            "bloqueada": prescription.bloqueada,
            "justificacion": prescription.justificacion,
            "fecha_creacion": prescription.fecha_creacion,
            "fecha_actualizacion": prescription.fecha_actualizacion,
            "paciente_nombre": (
                f"{prescription.paciente.nombre} {prescription.paciente.apellido}"
                if prescription.paciente
                else None
            ),
            "medico_nombre": (
                f"{prescription.medico.nombre} {prescription.medico.apellido}"
                if prescription.medico
                else None
            ),
            "items": [
                {
                    "id_item": item.id_item,
                    "id_medicamento": item.id_medicamento,
                    "cantidad": item.cantidad,
                    "dosis": item.dosis,
                    "frecuencia": item.frecuencia,
                    "instrucciones": item.instrucciones,
                    "estado": item.estado,
                    "medicamento_nombre": item.medicamento.nombre if item.medicamento else None,
                }
                for item in prescription.items
            ],
        }

    def list_prescriptions(
        self,
        patient_id: int | None = None,
        estado: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        skip = (page - 1) * page_size
        items, total = self.repository.get_all(
            patient_id=patient_id, estado=estado, skip=skip, limit=page_size
        )
        return [self.serialize(item) for item in items], total

    def get_prescription(self, prescription_id: int) -> dict:
        prescription = self.repository.get_by_id(prescription_id)
        if not prescription:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        return self.serialize(prescription)

    def create_prescription(self, data: dict, current_user: User) -> dict:
        if not self.patient_repository.get_by_id(data["id_paciente"]):
            raise HTTPException(status_code=404, detail="Paciente no encontrado")

        if data.get("id_diagnostico") is not None:
            if not self.diagnosis_repository.get_by_id(data["id_diagnostico"]):
                raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")

        items_data = data["items"]
        if not items_data:
            raise HTTPException(status_code=400, detail="La receta debe incluir al menos un medicamento")

        # Validar que todos los medicamentos existan y estén activos antes de persistir.
        medication_ids = [item["id_medicamento"] for item in items_data]
        medications = (
            self.db.query(Medication)
            .filter(Medication.id_medicamento.in_(medication_ids))
            .all()
        )
        found_ids = {medication.id_medicamento for medication in medications}
        missing = set(medication_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Medicamentos no encontrados: {sorted(missing)}",
            )

        # Toda la receta y sus ítems se guardan en una sola transacción.
        try:
            prescription = Prescription(
                id_paciente=data["id_paciente"],
                id_usuario=current_user.id_usuario,
                id_diagnostico=data.get("id_diagnostico"),
                fecha_emision=data.get("fecha_emision"),
                notas=data.get("notas"),
                estado="active",
                id_usuario_creacion=current_user.id_usuario,
            )
            for item in items_data:
                prescription.items.append(
                    PrescriptionItem(
                        id_medicamento=item["id_medicamento"],
                        cantidad=item.get("cantidad"),
                        dosis=item.get("dosis"),
                        frecuencia=item.get("frecuencia"),
                        instrucciones=item.get("instrucciones"),
                        estado="active",
                    )
                )
            self.db.add(prescription)
            self.db.flush()
            log_action(self.db, current_user, "crear", "receta", prescription.id_receta)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return self.get_prescription(prescription.id_receta)

    def update_prescription(self, prescription_id: int, data: dict, current_user: User) -> dict:
        prescription = self.repository.get_by_id(prescription_id)
        if not prescription:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        if prescription.estado == "cancelled":
            raise HTTPException(status_code=400, detail="No se puede modificar una receta cancelada")

        if data.get("id_diagnostico") is not None:
            if not self.diagnosis_repository.get_by_id(data["id_diagnostico"]):
                raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
            prescription.id_diagnostico = data["id_diagnostico"]
        if data.get("fecha_emision") is not None:
            prescription.fecha_emision = data["fecha_emision"]
        if data.get("notas") is not None:
            prescription.notas = data["notas"]

        log_action(self.db, current_user, "actualizar", "receta", prescription.id_receta)
        self.db.commit()
        return self.get_prescription(prescription_id)

    def change_status(self, prescription_id: int, estado: str, current_user: User) -> dict:
        prescription = self.repository.get_by_id(prescription_id)
        if not prescription:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        prescription.estado = estado
        log_action(self.db, current_user, f"estado:{estado}", "receta", prescription.id_receta)
        self.db.commit()
        return self.get_prescription(prescription_id)
