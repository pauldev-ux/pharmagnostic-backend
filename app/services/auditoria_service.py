"""Servicio reutilizable de auditoría.

Una sola función `registrar()` centraliza el registro de acciones importantes para
no repetir código en cada router/servicio. La IP de origen se obtiene de un
ContextVar que alimenta un middleware (ver app.main), de modo que los servicios no
necesitan recibir el objeto Request.
"""

from contextvars import ContextVar
from typing import Optional

from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria

# IP de la petición en curso (la fija el middleware de la app).
_current_ip: ContextVar[Optional[str]] = ContextVar("current_ip", default=None)


def set_current_ip(ip: Optional[str]) -> None:
    _current_ip.set(ip)


def get_current_ip() -> Optional[str]:
    return _current_ip.get()


def registrar(
    db: Session,
    *,
    accion: str,
    modulo: str,
    tabla_afectada: Optional[str] = None,
    id_registro: Optional[int] = None,
    detalle: Optional[str] = None,
    user_id: Optional[int] = None,
    commit: bool = False,
) -> Auditoria:
    """Registra una entrada de auditoría.

    El `detalle` debe ser breve: NO incluir contraseñas, tokens, audios ni datos
    clínicos innecesarios. Por defecto no hace commit (se persiste con la
    transacción que lo invoca); usar commit=True en acciones sin transacción propia.
    """
    registro = Auditoria(
        id_usuario=user_id,
        accion=accion,
        modulo=modulo,
        tabla_afectada=tabla_afectada,
        id_registro=id_registro,
        detalle=detalle,
        ip_origen=get_current_ip(),
    )
    db.add(registro)
    if commit:
        db.commit()
        db.refresh(registro)
    return registro
