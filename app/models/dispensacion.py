from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base

# Estados de la dispensación.
ESTADO_DISPENSACION_VALUES = ("pendiente", "confirmada", "rechazada")


class Dispensacion(Base):
    __tablename__ = "dispensacion"

    id_dispensacion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_receta = Column(Integer, ForeignKey("prescriptions.id_receta"), nullable=False, index=True)
    id_usuario_farmaceutico = Column(Integer, ForeignKey("users.id_usuario"), nullable=True)
    codigo_verificacion = Column(String(128), nullable=False, unique=True, index=True)
    estado = Column(String(20), nullable=False, default="pendiente")
    observaciones = Column(Text, nullable=True)
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_dispensacion = Column(DateTime, nullable=True)

    receta = relationship("Prescription", back_populates="dispensaciones")
    farmaceutico = relationship("User", foreign_keys=[id_usuario_farmaceutico])
