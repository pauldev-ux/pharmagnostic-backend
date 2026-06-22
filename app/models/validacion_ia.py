from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class ValidacionIA(Base):
    __tablename__ = "validacion_ia"

    id_validacion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_receta = Column(Integer, ForeignKey("prescriptions.id_receta"), nullable=False, index=True)
    id_audio = Column(Integer, ForeignKey("audio_clinico.id_audio"), nullable=True)
    nivel_riesgo = Column(Integer, nullable=False, default=0)
    resumen = Column(Text, nullable=True)
    # Listas estructuradas (JSONB) con los hallazgos.
    interacciones = Column(JSONB, nullable=True, default=list)
    contraindicaciones = Column(JSONB, nullable=True, default=list)
    duplicidades = Column(JSONB, nullable=True, default=list)
    errores_dosis = Column(JSONB, nullable=True, default=list)
    inconsistencias_audio = Column(JSONB, nullable=True, default=list)
    fuentes_rag = Column(JSONB, nullable=True, default=list)
    fecha_validacion = Column(DateTime, nullable=False, default=datetime.utcnow)

    receta = relationship("Prescription", back_populates="validaciones")
    audio = relationship("AudioClinico", foreign_keys=[id_audio])
