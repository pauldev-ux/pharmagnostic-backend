from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuditoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_auditoria: int
    id_usuario: Optional[int] = None
    usuario_nombre: Optional[str] = None
    accion: str
    modulo: str
    tabla_afectada: Optional[str] = None
    id_registro: Optional[int] = None
    detalle: Optional[str] = None
    ip_origen: Optional[str] = None
    fecha_accion: datetime
