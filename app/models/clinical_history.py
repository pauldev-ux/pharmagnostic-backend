from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ClinicalHistory(Base):
    __tablename__ = "clinical_history"

    id_historial = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_paciente = Column(Integer, ForeignKey("patients.id_paciente"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    tipo_evento = Column(String(50), nullable=False)
    descripcion = Column(Text, nullable=False)
    fecha_evento = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    activo = Column(Boolean, nullable=False, default=True)

    paciente = relationship("Patient", back_populates="historial")
    usuario = relationship("User", foreign_keys=[id_usuario])
