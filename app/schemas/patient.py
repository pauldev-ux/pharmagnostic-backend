from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

SEXO_VALUES = ("masculino", "femenino", "otro", "no_especificado")
FUNCION_VALUES = ("normal", "leve", "moderada", "severa", "desconocida")

_SEXO_PATTERN = "^(masculino|femenino|otro|no_especificado)$"
_FUNCION_PATTERN = "^(normal|leve|moderada|severa|desconocida)$"


def _calcular_edad(fecha_nacimiento: date, hoy: Optional[date] = None) -> int:
    hoy = hoy or date.today()
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return max(edad, 0)


class PatientBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    fecha_nacimiento: date
    sexo: str = Field(default="no_especificado", pattern=_SEXO_PATTERN)
    telefono: Optional[str] = Field(default=None, max_length=30)
    correo: Optional[EmailStr] = None
    peso_kg: Optional[Decimal] = Field(default=None, gt=0, le=999)
    funcion_renal: str = Field(default="desconocida", pattern=_FUNCION_PATTERN)
    funcion_hepatica: str = Field(default="desconocida", pattern=_FUNCION_PATTERN)
    alergias: Optional[str] = None
    antecedentes_medicos: Optional[str] = None
    observaciones: Optional[str] = None

    @field_validator("fecha_nacimiento")
    @classmethod
    def fecha_no_futura(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        return value


class PatientCreate(PatientBase):
    ci: str = Field(min_length=1, max_length=20)
    id_usuario: Optional[int] = None  # cuenta de acceso del paciente (portal)


class PatientUpdate(BaseModel):
    id_usuario: Optional[int] = None
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(default=None, min_length=1, max_length=100)
    ci: Optional[str] = Field(default=None, min_length=1, max_length=20)
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[str] = Field(default=None, pattern=_SEXO_PATTERN)
    telefono: Optional[str] = Field(default=None, max_length=30)
    correo: Optional[EmailStr] = None
    peso_kg: Optional[Decimal] = Field(default=None, gt=0, le=999)
    funcion_renal: Optional[str] = Field(default=None, pattern=_FUNCION_PATTERN)
    funcion_hepatica: Optional[str] = Field(default=None, pattern=_FUNCION_PATTERN)
    alergias: Optional[str] = None
    antecedentes_medicos: Optional[str] = None
    observaciones: Optional[str] = None

    @field_validator("fecha_nacimiento")
    @classmethod
    def fecha_no_futura(cls, value: Optional[date]) -> Optional[date]:
        if value is not None and value > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        return value


class PatientStatusUpdate(BaseModel):
    activo: bool


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_paciente: int
    nombre: str
    apellido: str
    ci: str
    fecha_nacimiento: date
    sexo: str
    telefono: Optional[str] = None
    correo: Optional[str] = None
    peso_kg: Optional[Decimal] = None
    funcion_renal: str
    funcion_hepatica: str
    alergias: Optional[str] = None
    antecedentes_medicos: Optional[str] = None
    observaciones: Optional[str] = None
    activo: bool
    id_usuario: Optional[int] = None
    fecha_registro: datetime
    fecha_actualizacion: Optional[datetime] = None
    id_usuario_registro: Optional[int] = None
    id_usuario_actualizacion: Optional[int] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def edad(self) -> int:
        return _calcular_edad(self.fecha_nacimiento)
