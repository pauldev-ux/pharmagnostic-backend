from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Medication(Base):
    __tablename__ = "medications"

    id_medicamento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(150), nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    dosis = Column(String(100), nullable=True)
    presentacion = Column(String(100), nullable=True)
    precio = Column(Numeric(10, 2), nullable=True)
    estado = Column(String(20), nullable=False, default="active", index=True)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    id_usuario_creacion = Column(Integer, ForeignKey("users.id_usuario"), nullable=True)

    items = relationship("PrescriptionItem", back_populates="medicamento")
    creador = relationship("User", foreign_keys=[id_usuario_creacion])
