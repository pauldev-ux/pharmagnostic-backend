from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base

# Valores permitidos (validados en los schemas Pydantic).
SEXO_VALUES = ("masculino", "femenino", "otro", "no_especificado")
FUNCION_VALUES = ("normal", "leve", "moderada", "severa", "desconocida")


class Patient(Base):
    __tablename__ = "patients"

    id_paciente = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    ci = Column(String(20), nullable=False, unique=True, index=True)
    fecha_nacimiento = Column(Date, nullable=False)
    sexo = Column(String(20), nullable=False, default="no_especificado")
    telefono = Column(String(30), nullable=True)
    correo = Column(String(150), nullable=True, index=True)
    peso_kg = Column(Numeric(5, 2), nullable=True)
    funcion_renal = Column(String(20), nullable=False, default="desconocida")
    funcion_hepatica = Column(String(20), nullable=False, default="desconocida")
    alergias = Column(Text, nullable=True)
    antecedentes_medicos = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True, index=True)
    # Cuenta de acceso del paciente (portal). Un registro clínico por cuenta.
    id_usuario = Column(Integer, ForeignKey("users.id_usuario"), nullable=True, unique=True)
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    id_usuario_registro = Column(Integer, ForeignKey("users.id_usuario"), nullable=True)
    id_usuario_actualizacion = Column(Integer, ForeignKey("users.id_usuario"), nullable=True)

    diagnoses = relationship("Diagnosis", back_populates="paciente")
    historial = relationship("ClinicalHistory", back_populates="paciente")
    prescriptions = relationship("Prescription", back_populates="paciente")
    cuenta = relationship("User", foreign_keys=[id_usuario])
    registrado_por = relationship("User", foreign_keys=[id_usuario_registro])
    actualizado_por = relationship("User", foreign_keys=[id_usuario_actualizacion])
