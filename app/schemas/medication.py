from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MedicationCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: Optional[str] = None
    dosis: Optional[str] = Field(default=None, max_length=100)
    presentacion: Optional[str] = Field(default=None, max_length=100)
    precio: Optional[Decimal] = Field(default=None, ge=0)


class MedicationUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=150)
    descripcion: Optional[str] = None
    dosis: Optional[str] = Field(default=None, max_length=100)
    presentacion: Optional[str] = Field(default=None, max_length=100)
    precio: Optional[Decimal] = Field(default=None, ge=0)


class MedicationStatusUpdate(BaseModel):
    estado: str = Field(pattern="^(active|inactive)$")


class MedicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_medicamento: int
    nombre: str
    descripcion: Optional[str] = None
    dosis: Optional[str] = None
    presentacion: Optional[str] = None
    precio: Optional[Decimal] = None
    estado: str
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
