from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TimelineEvent(BaseModel):
    evento: str
    fecha: Optional[datetime] = None
    usuario: Optional[str] = None
    detalle: Optional[str] = None


class RecipeTimeline(BaseModel):
    id_receta: int
    eventos: list[TimelineEvent] = []
