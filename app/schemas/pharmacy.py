from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class DispensacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_dispensacion: int
    id_receta: int
    id_usuario_farmaceutico: Optional[int] = None
    codigo_verificacion: str
    estado: str
    observaciones: Optional[str] = None
    fecha_registro: datetime
    fecha_dispensacion: Optional[datetime] = None


class QrResponse(BaseModel):
    id_dispensacion: int
    id_receta: int
    codigo_verificacion: str
    url_verificacion: str
    qr_base64: str
    estado: str


class PharmacyRecipeItem(BaseModel):
    id_receta: int
    id_dispensacion: int
    codigo_verificacion: str
    estado_dispensacion: str
    estado_receta: str
    paciente_nombre: Optional[str] = None
    medico_nombre: Optional[str] = None
    nivel_riesgo: int
    fecha_emision: Optional[Any] = None
    fecha_registro: datetime


class PharmacyRecipeDetail(BaseModel):
    receta: dict
    dispensacion: Optional[DispensacionOut] = None
    alertas: list[Any] = []
    validada: bool = False


class VerifyQrRequest(BaseModel):
    codigo: str = Field(min_length=1)


class VerifyQrResponse(BaseModel):
    estado_qr: str  # valido | invalido | anulado | usado
    mensaje: str
    id_receta: Optional[int] = None
    id_dispensacion: Optional[int] = None


class DispenseRequest(BaseModel):
    codigo_verificacion: Optional[str] = None
    observaciones: Optional[str] = None


class RejectRequest(BaseModel):
    observaciones: str = Field(min_length=3)
