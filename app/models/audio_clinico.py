from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base

# Estados de procesamiento permitidos.
ESTADO_PROCESAMIENTO_VALUES = ("pendiente", "procesando", "completado", "error")


class AudioClinico(Base):
    __tablename__ = "audio_clinico"

    id_audio = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_receta = Column(Integer, ForeignKey("prescriptions.id_receta"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    ruta_archivo = Column(String(500), nullable=False)
    formato = Column(String(20), nullable=False)
    duracion_segundos = Column(Integer, nullable=True)
    transcripcion = Column(Text, nullable=True)
    estado_procesamiento = Column(String(20), nullable=False, default="pendiente")
    fecha_grabacion = Column(DateTime, nullable=False, default=datetime.utcnow)

    receta = relationship("Prescription", back_populates="audios")
    usuario = relationship("User", foreign_keys=[id_usuario])
