from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def log_action(
    db: Session,
    user: User,
    accion: str,
    entidad: str,
    entidad_id: Optional[int] = None,
    detalle: Optional[str] = None,
) -> None:
    """Registra una acción en la bitácora de auditoría.

    No hace commit por sí mismo: se persiste junto a la transacción que lo invoca.
    """
    db.add(
        AuditLog(
            id_usuario=user.id_usuario,
            id_rol=user.id_rol,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            detalle=detalle,
        )
    )
