from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PrescriptionItemCreate(BaseModel):
    id_medicamento: int
    cantidad: Optional[int] = Field(default=None, ge=1)
    dosis: Optional[str] = Field(default=None, max_length=100)
    frecuencia: Optional[str] = Field(default=None, max_length=100)
    instrucciones: Optional[str] = None


class PrescriptionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_item: int
    id_medicamento: int
    cantidad: Optional[int] = None
    dosis: Optional[str] = None
    frecuencia: Optional[str] = None
    instrucciones: Optional[str] = None
    estado: str
    medicamento_nombre: Optional[str] = None


class PrescriptionCreate(BaseModel):
    id_paciente: int
    id_diagnostico: Optional[int] = None
    fecha_emision: Optional[date] = None
    notas: Optional[str] = None
    items: list[PrescriptionItemCreate] = Field(min_length=1)


class PrescriptionUpdate(BaseModel):
    id_diagnostico: Optional[int] = None
    fecha_emision: Optional[date] = None
    notas: Optional[str] = None


class PrescriptionStatusUpdate(BaseModel):
    estado: str = Field(pattern="^(active|cancelled)$")


class PrescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_receta: int
    id_paciente: int
    id_usuario: int
    id_diagnostico: Optional[int] = None
    fecha_emision: date
    notas: Optional[str] = None
    estado: str
    nivel_riesgo: int = 0
    bloqueada: bool = False
    justificacion: Optional[str] = None
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
    paciente_nombre: Optional[str] = None
    medico_nombre: Optional[str] = None
    items: list[PrescriptionItemOut] = []
