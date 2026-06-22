from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base

# Niveles de riesgo: 0 sin alertas, 1 leve, 2 importante, 3 crítico.
NIVEL_VALUES = (0, 1, 2, 3)


class AlertaClinica(Base):
    __tablename__ = "alerta_clinica"

    id_alerta = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_receta = Column(Integer, ForeignKey("prescriptions.id_receta"), nullable=False)
    id_audio = Column(Integer, ForeignKey("audio_clinico.id_audio"), nullable=True)
    tipo_alerta = Column(String(50), nullable=False)
    nivel = Column(Integer, nullable=False, default=0)
    descripcion = Column(Text, nullable=False)
    recomendacion = Column(Text, nullable=True)
    revisada = Column(Boolean, nullable=False, default=False)
    fecha_generacion = Column(DateTime, nullable=False, default=datetime.utcnow)

    receta = relationship("Prescription", back_populates="alertas")
    audio = relationship("AudioClinico", foreign_keys=[id_audio])
