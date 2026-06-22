from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Tipos de evento permitidos para el historial clínico.
TIPO_EVENTO_VALUES = (
    "antecedente",
    "alergia",
    "hospitalizacion",
    "cirugia",
    "enfermedad_cronica",
    "evento_adverso",
    "observacion",
    "otro",
)
_TIPO_EVENTO_PATTERN = (
    "^(antecedente|alergia|hospitalizacion|cirugia|enfermedad_cronica|evento_adverso|observacion|otro)$"
)


class ClinicalHistoryCreate(BaseModel):
    tipo_evento: str = Field(pattern=_TIPO_EVENTO_PATTERN)
    descripcion: str = Field(min_length=1)
    fecha_evento: Optional[datetime] = None


class ClinicalHistoryUpdate(BaseModel):
    tipo_evento: Optional[str] = Field(default=None, pattern=_TIPO_EVENTO_PATTERN)
    descripcion: Optional[str] = Field(default=None, min_length=1)
    fecha_evento: Optional[datetime] = None


class ClinicalHistoryStatusUpdate(BaseModel):
    activo: bool


class ClinicalHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_historial: int
    id_paciente: int
    id_usuario: int
    tipo_evento: str
    descripcion: str
    fecha_evento: datetime
    fecha_registro: datetime
    activo: bool
