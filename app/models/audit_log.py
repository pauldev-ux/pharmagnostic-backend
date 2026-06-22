from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id_auditoria = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    id_rol = Column(Integer, ForeignKey("roles.id_rol"), nullable=True)
    accion = Column(String(100), nullable=False)
    entidad = Column(String(50), nullable=True)
    entidad_id = Column(Integer, nullable=True)
    detalle = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)

    usuario = relationship("User", back_populates="audit_logs")
    rol = relationship("Role", back_populates="audit_logs")
