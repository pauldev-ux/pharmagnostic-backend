from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

TIPO_DIAGNOSTICO_VALUES = ("preliminar", "confirmado", "diferencial")
_TIPO_PATTERN = "^(preliminar|confirmado|diferencial)$"


class DiagnosisCreate(BaseModel):
    codigo_cie10: Optional[str] = Field(default=None, max_length=10)
    descripcion: str = Field(min_length=1)
    tipo: str = Field(default="preliminar", pattern=_TIPO_PATTERN)
    observaciones: Optional[str] = None
    fecha_diagnostico: Optional[datetime] = None


class DiagnosisUpdate(BaseModel):
    codigo_cie10: Optional[str] = Field(default=None, max_length=10)
    descripcion: Optional[str] = Field(default=None, min_length=1)
    tipo: Optional[str] = Field(default=None, pattern=_TIPO_PATTERN)
    observaciones: Optional[str] = None
    fecha_diagnostico: Optional[datetime] = None


class DiagnosisStatusUpdate(BaseModel):
    activo: bool


class DiagnosisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_diagnostico: int
    id_paciente: int
    id_usuario: int
    codigo_cie10: Optional[str] = None
    descripcion: str
    tipo: str
    observaciones: Optional[str] = None
    fecha_diagnostico: datetime
    fecha_registro: datetime
    fecha_actualizacion: Optional[datetime] = None
    activo: bool
