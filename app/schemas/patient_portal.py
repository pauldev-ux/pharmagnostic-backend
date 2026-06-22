from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

DISCLAIMER = "Este asistente es informativo y no sustituye la orientación de un profesional de salud."
REFUSAL = "No puedo realizar diagnósticos ni modificar tu tratamiento. Consulta con tu médico."


class PortalProfile(BaseModel):
    id_paciente: int
    nombre: str
    apellido: str
    ci: str
    sexo: str
    fecha_nacimiento: date
    edad: int
    correo: Optional[str] = None
    telefono: Optional[str] = None


class PortalMedicamento(BaseModel):
    nombre: str
    dosis: Optional[str] = None
    frecuencia: Optional[str] = None
    indicaciones: Optional[str] = None  # vía / duración / instrucciones


class PortalRecipeItem(BaseModel):
    id_receta: int
    fecha_emision: Optional[date] = None
    estado: str  # borrador | validada | bloqueada | dispensada | anulada
    nivel_riesgo: int
    estado_dispensacion: str  # sin_generar | pendiente | confirmada | rechazada
    total_medicamentos: int


class PortalRecipeDetail(BaseModel):
    id_receta: int
    fecha_emision: Optional[date] = None
    estado: str
    nivel_riesgo: int
    estado_dispensacion: str
    medicamentos: list[PortalMedicamento] = []


class ChatRequest(BaseModel):
    mensaje: str = Field(min_length=1, max_length=500)


class ChatResponse(BaseModel):
    respuesta: str
    disclaimer: str = DISCLAIMER
