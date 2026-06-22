from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id_item = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_receta = Column(Integer, ForeignKey("prescriptions.id_receta"), nullable=False)
    id_medicamento = Column(Integer, ForeignKey("medications.id_medicamento"), nullable=False)
    cantidad = Column(Integer, nullable=True)
    dosis = Column(String(100), nullable=True)
    frecuencia = Column(String(100), nullable=True)
    instrucciones = Column(Text, nullable=True)
    estado = Column(String(20), nullable=False, default="active")
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    receta = relationship("Prescription", back_populates="items")
    medicamento = relationship("Medication", back_populates="items")
