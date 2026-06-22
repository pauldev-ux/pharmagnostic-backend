from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.user import User
from app.repositories.dispensacion_repository import DispensacionRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.schemas.patient_portal import DISCLAIMER, REFUSAL
from app.services import ollama_client
from app.services.ollama_client import OllamaError

# Patrones que indican una consulta médica fuera de alcance (diagnóstico/tratamiento).
_OUT_OF_SCOPE = (
    "diagn",
    "sintoma",
    "síntoma",
    "me duele",
    "dolor de",
    "tengo fiebre",
    "recomien",
    "qué me das",
    "que me das",
    "puedo tomar",
    "debo tomar",
    "qué tomo para",
    "que tomo para",
    "cambiar la dosis",
    "cambiar dosis",
    "subir la dosis",
    "bajar la dosis",
    "aumentar la dosis",
    "qué enfermedad",
    "que enfermedad",
    "tratamiento para",
    "cura para",
    "interpreta",
    "es grave",
)


def _edad(fn: date) -> int:
    hoy = date.today()
    return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))


class PatientPortalService:
    def __init__(self, db: Session):
        self.db = db
        self.patient_repository = PatientRepository(db)
        self.prescription_repository = PrescriptionRepository(db)
        self.dispensacion_repository = DispensacionRepository(db)

    def _my_patient(self, current_user: User) -> Patient:
        patient = self.patient_repository.get_by_user(current_user.id_usuario)
        if not patient:
            raise HTTPException(
                status_code=404,
                detail="No hay un registro de paciente asociado a tu cuenta.",
            )
        return patient

    @staticmethod
    def _estado_visible(recipe) -> str:
        if recipe.estado == "cancelled":
            return "anulada"
        if recipe.estado == "dispensada":
            return "dispensada"
        if recipe.bloqueada:
            return "bloqueada"
        if recipe.validaciones:
            return "validada"
        return "borrador"

    def _estado_dispensacion(self, recipe_id: int) -> str:
        disp = self.dispensacion_repository.get_latest_for_recipe(recipe_id)
        return disp.estado if disp else "sin_generar"

    # --- Endpoints ---
    def profile(self, current_user: User) -> dict:
        patient = self._my_patient(current_user)
        return {
            "id_paciente": patient.id_paciente,
            "nombre": patient.nombre,
            "apellido": patient.apellido,
            "ci": patient.ci,
            "sexo": patient.sexo,
            "fecha_nacimiento": patient.fecha_nacimiento,
            "edad": _edad(patient.fecha_nacimiento),
            "correo": patient.correo,
            "telefono": patient.telefono,
        }

    def list_recipes(self, current_user: User) -> list[dict]:
        patient = self._my_patient(current_user)
        recipes, _ = self.prescription_repository.get_all(patient_id=patient.id_paciente, limit=200)
        return [
            {
                "id_receta": r.id_receta,
                "fecha_emision": r.fecha_emision,
                "estado": self._estado_visible(r),
                "nivel_riesgo": r.nivel_riesgo,
                "estado_dispensacion": self._estado_dispensacion(r.id_receta),
                "total_medicamentos": len(r.items),
            }
            for r in recipes
        ]

    def get_recipe(self, recipe_id: int, current_user: User) -> dict:
        patient = self._my_patient(current_user)
        recipe = self.prescription_repository.get_by_id(recipe_id)
        # Validación de propiedad en el backend (no se confía en el ID del frontend).
        if not recipe or recipe.id_paciente != patient.id_paciente:
            raise HTTPException(status_code=404, detail="Receta no encontrada")

        medicamentos = [
            {
                "nombre": item.medicamento.nombre if item.medicamento else f"#{item.id_medicamento}",
                "dosis": item.dosis,
                "frecuencia": item.frecuencia,
                "indicaciones": item.instrucciones,
            }
            for item in recipe.items
        ]
        return {
            "id_receta": recipe.id_receta,
            "fecha_emision": recipe.fecha_emision,
            "estado": self._estado_visible(recipe),
            "nivel_riesgo": recipe.nivel_riesgo,
            "estado_dispensacion": self._estado_dispensacion(recipe.id_receta),
            "medicamentos": medicamentos,
        }

    # --- Chatbot informativo ---
    def chat(self, mensaje: str, current_user: User) -> dict:
        texto = mensaje.strip().lower()
        if any(p in texto for p in _OUT_OF_SCOPE):
            return {"respuesta": REFUSAL, "disclaimer": DISCLAIMER}

        # Contexto: SOLO datos autorizados del paciente autenticado.
        recetas = self.list_recipes(current_user)
        if recetas:
            lineas = []
            for r in recetas:
                detalle = self.get_recipe(r["id_receta"], current_user)
                meds = ", ".join(
                    f"{m['nombre']} (dosis {m['dosis'] or 'N/D'}, {m['frecuencia'] or 'N/D'})"
                    for m in detalle["medicamentos"]
                )
                lineas.append(
                    f"Receta #{r['id_receta']} | estado: {r['estado']} | "
                    f"dispensación: {r['estado_dispensacion']} | medicamentos: {meds or 'sin medicamentos'}"
                )
            contexto = "\n".join(lineas)
        else:
            contexto = "El paciente no tiene recetas registradas."

        system = (
            "Eres un asistente INFORMATIVO del portal del paciente. Solo puedes informar sobre: el "
            "estado de las recetas del paciente, los medicamentos ya prescritos, sus dosis e "
            "indicaciones ya registradas, el proceso de validación, el estado de dispensación, los "
            "pasos para recoger la receta y el funcionamiento general del sistema. NUNCA diagnostiques, "
            "no interpretes síntomas, no recomiendes ni cambies medicamentos o dosis, no reemplaces al "
            "médico. Usa EXCLUSIVAMENTE el CONTEXTO del paciente. Si te piden algo médico fuera de "
            f"alcance responde exactamente: '{REFUSAL}'. Responde en español, breve y claro."
        )
        prompt = f"CONTEXTO DEL PACIENTE:\n{contexto}\n\nPREGUNTA: {mensaje}"

        try:
            respuesta = ollama_client.chat(system, prompt)
        except OllamaError:
            raise HTTPException(status_code=503, detail="El asistente no está disponible en este momento")

        return {"respuesta": respuesta, "disclaimer": DISCLAIMER}
