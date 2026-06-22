from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id_receta = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_paciente = Column(Integer, ForeignKey("patients.id_paciente"), nullable=False, index=True)
    id_usuario = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    id_diagnostico = Column(Integer, ForeignKey("diagnoses.id_diagnostico"), nullable=True)
    fecha_emision = Column(Date, nullable=False, default=datetime.utcnow)
    notas = Column(Text, nullable=True)
    estado = Column(String(20), nullable=False, default="active", index=True)
    # Nivel de riesgo de la última validación (0 sin alertas .. 3 crítico).
    nivel_riesgo = Column(Integer, nullable=False, default=0)
    # Una receta con nivel 3 queda bloqueada hasta corrección o justificación médica.
    bloqueada = Column(Boolean, nullable=False, default=False)
    justificacion = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    fecha_actualizacion = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    id_usuario_creacion = Column(Integer, ForeignKey("users.id_usuario"), nullable=True)

    paciente = relationship("Patient", back_populates="prescriptions")
    diagnostico = relationship("Diagnosis", foreign_keys=[id_diagnostico])
    medico = relationship("User", foreign_keys=[id_usuario])
    creador = relationship("User", foreign_keys=[id_usuario_creacion])
    items = relationship(
        "PrescriptionItem",
        back_populates="receta",
        cascade="all, delete-orphan",
    )
    audios = relationship(
        "AudioClinico",
        back_populates="receta",
        cascade="all, delete-orphan",
    )
    alertas = relationship(
        "AlertaClinica",
        back_populates="receta",
        cascade="all, delete-orphan",
    )
    validaciones = relationship(
        "ValidacionIA",
        back_populates="receta",
        cascade="all, delete-orphan",
    )
    dispensaciones = relationship(
        "Dispensacion",
        back_populates="receta",
        cascade="all, delete-orphan",
    )
