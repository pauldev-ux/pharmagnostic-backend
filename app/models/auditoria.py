from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id_auditoria = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("users.id_usuario"), nullable=True, index=True)
    accion = Column(String(80), nullable=False, index=True)
    modulo = Column(String(50), nullable=False, index=True)
    tabla_afectada = Column(String(50), nullable=True)
    id_registro = Column(Integer, nullable=True)
    detalle = Column(Text, nullable=True)
    ip_origen = Column(String(50), nullable=True)
    fecha_accion = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    usuario = relationship("User", foreign_keys=[id_usuario])
