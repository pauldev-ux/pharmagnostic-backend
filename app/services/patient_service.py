from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.user import User
from app.repositories.patient_repository import PatientRepository
from app.services.audit_service import log_action


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PatientRepository(db)

    def list_patients(
        self,
        search: str | None = None,
        activo: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Patient], int]:
        skip = (page - 1) * page_size
        return self.repository.get_all(search=search, activo=activo, skip=skip, limit=page_size)

    def get_patient(self, patient_id: int) -> Patient:
        patient = self.repository.get_by_id(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        return patient

    def _validate_account_link(self, id_usuario, exclude_patient_id=None) -> None:
        if id_usuario is None:
            return
        from app.repositories.user_repository import UserRepository

        user = UserRepository(self.db).get_by_id(id_usuario)
        if not user:
            raise HTTPException(status_code=404, detail="Cuenta de usuario no encontrada")
        if user.rol.nombre != "patient":
            raise HTTPException(status_code=400, detail="La cuenta a vincular debe tener rol paciente")
        existing = self.repository.get_by_user(id_usuario)
        if existing and existing.id_paciente != exclude_patient_id:
            raise HTTPException(status_code=409, detail="La cuenta ya está vinculada a otro paciente")

    def create_patient(self, data: dict, current_user: User) -> Patient:
        ci = data["ci"].strip()
        if self.repository.get_by_ci(ci):
            raise HTTPException(status_code=409, detail="El CI ya está registrado")

        self._validate_account_link(data.get("id_usuario"))
        correo = data.get("correo")
        patient = Patient(
            nombre=data["nombre"].strip(),
            apellido=data["apellido"].strip(),
            ci=ci,
            id_usuario=data.get("id_usuario"),
            fecha_nacimiento=data["fecha_nacimiento"],
            sexo=data.get("sexo", "no_especificado"),
            telefono=data.get("telefono"),
            correo=correo.lower() if correo else None,
            peso_kg=data.get("peso_kg"),
            funcion_renal=data.get("funcion_renal", "desconocida"),
            funcion_hepatica=data.get("funcion_hepatica", "desconocida"),
            alergias=data.get("alergias"),
            antecedentes_medicos=data.get("antecedentes_medicos"),
            observaciones=data.get("observaciones"),
            activo=True,
            id_usuario_registro=current_user.id_usuario,
        )
        self.db.add(patient)
        self.db.flush()
        log_action(self.db, current_user, "crear", "paciente", patient.id_paciente)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def update_patient(self, patient_id: int, data: dict, current_user: User) -> Patient:
        patient = self.get_patient(patient_id)

        if "ci" in data and data["ci"] is not None:
            ci = data["ci"].strip()
            existing = self.repository.get_by_ci(ci)
            if existing and existing.id_paciente != patient_id:
                raise HTTPException(status_code=409, detail="El CI ya está registrado")
            patient.ci = ci

        if "correo" in data and data["correo"] is not None:
            patient.correo = data["correo"].lower()

        if "id_usuario" in data:
            self._validate_account_link(data["id_usuario"], exclude_patient_id=patient_id)
            patient.id_usuario = data["id_usuario"]

        simple_fields = (
            "nombre",
            "apellido",
            "fecha_nacimiento",
            "sexo",
            "telefono",
            "peso_kg",
            "funcion_renal",
            "funcion_hepatica",
            "alergias",
            "antecedentes_medicos",
            "observaciones",
        )
        for field in simple_fields:
            if field in data and data[field] is not None:
                setattr(patient, field, data[field])

        patient.id_usuario_actualizacion = current_user.id_usuario
        log_action(self.db, current_user, "actualizar", "paciente", patient.id_paciente)
        return self.repository.update(patient)

    def change_status(self, patient_id: int, activo: bool, current_user: User) -> Patient:
        patient = self.get_patient(patient_id)
        patient.activo = activo
        patient.id_usuario_actualizacion = current_user.id_usuario
        accion = "activar" if activo else "desactivar"
        log_action(self.db, current_user, accion, "paciente", patient.id_paciente)
        return self.repository.update(patient)
