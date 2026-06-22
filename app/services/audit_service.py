from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import auditoria_service

# Mapea la "entidad" usada por los servicios clínicos a (módulo, tabla afectada).
_ENTIDAD_MAP = {
    "paciente": ("pacientes", "patients"),
    "diagnostico": ("diagnosticos", "diagnoses"),
    "medicamento": ("medicamentos", "medications"),
    "receta": ("recetas", "prescriptions"),
    "historial": ("historial_clinico", "clinical_history"),
}


def log_action(
    db: Session,
    user: User,
    accion: str,
    entidad: str,
    entidad_id: Optional[int] = None,
    detalle: Optional[str] = None,
) -> None:
    """Compatibilidad: registra en la auditoría central a partir de la entidad.

    No hace commit por sí mismo: se persiste junto a la transacción que lo invoca.
    """
    modulo, tabla = _ENTIDAD_MAP.get(entidad, (entidad, entidad))
    auditoria_service.registrar(
        db,
        accion=accion,
        modulo=modulo,
        tabla_afectada=tabla,
        id_registro=entidad_id,
        detalle=detalle,
        user_id=user.id_usuario if user else None,
        commit=False,
    )
