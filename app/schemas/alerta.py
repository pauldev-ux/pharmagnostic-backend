from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

# Mensaje obligatorio que acompaña toda prevalidación en esta etapa.
DISCLAIMER = "Validación preliminar de consistencia. No reemplaza la revisión médica."


class AlertaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_alerta: int
    id_receta: int
    id_audio: Optional[int] = None
    tipo_alerta: str
    nivel: int
    descripcion: str
    recomendacion: Optional[str] = None
    revisada: bool
    fecha_generacion: datetime


class AlertaReviewUpdate(BaseModel):
    revisada: bool = True


class PrevalidationResult(BaseModel):
    id_receta: int
    nivel_maximo: int
    total_alertas: int
    mensaje: str = DISCLAIMER
    alertas: list[AlertaOut] = []
