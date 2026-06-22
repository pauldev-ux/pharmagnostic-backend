from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AudioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_audio: int
    id_receta: int
    id_usuario: int
    ruta_archivo: str
    formato: str
    duracion_segundos: Optional[int] = None
    transcripcion: Optional[str] = None
    estado_procesamiento: str
    fecha_grabacion: datetime
