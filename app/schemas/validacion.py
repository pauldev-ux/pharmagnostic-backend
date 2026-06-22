from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

DISCLAIMER = "Esta validación es una herramienta de apoyo y no sustituye el criterio médico."


class ValidacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_validacion: int
    id_receta: int
    id_audio: Optional[int] = None
    nivel_riesgo: int
    resumen: Optional[str] = None
    interacciones: list[Any] = []
    contraindicaciones: list[Any] = []
    duplicidades: list[Any] = []
    errores_dosis: list[Any] = []
    inconsistencias_audio: list[Any] = []
    fuentes_rag: list[Any] = []
    fecha_validacion: datetime


class ValidacionResult(ValidacionOut):
    """Resultado de una validación recién ejecutada (incluye estado de bloqueo)."""

    bloqueada: bool = False
    mensaje: str = DISCLAIMER


class JustificarRequest(BaseModel):
    justificacion: str = Field(min_length=3)
