from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base

# Valores permitidos para el tipo de diagnóstico (validados en los schemas).
TIPO_DIAGNOSTICO_VALUES = ("preliminar", "confirmado", "diferencial")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id_diagnostico = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_paciente = Column(Integer, ForeignKey("patients.id_paciente"), nullable=False, index=True)
    id_usuario = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    codigo_cie10 = Column(String(10), nullable=True, index=True)
    descripcion = Column(Text, nullable=False)
    tipo = Column(String(20), nullable=False, default="preliminar")
    observaciones = Column(Text, nullable=True)
    fecha_diagnostico = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    activo = Column(Boolean, nullable=False, default=True)

    paciente = relationship("Patient", back_populates="diagnoses")
    medico = relationship("User", foreign_keys=[id_usuario])
