from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base

# Estados de procesamiento permitidos.
ESTADO_PROCESAMIENTO_VALUES = ("pendiente", "procesando", "procesado", "error")


class DocumentoFarmacologico(Base):
    __tablename__ = "documento_farmacologico"

    id_documento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    titulo = Column(String(255), nullable=False)
    tipo_documento = Column(String(50), nullable=True)
    fuente = Column(String(255), nullable=True)
    version = Column(String(50), nullable=True)
    nombre_archivo = Column(String(255), nullable=False)
    ruta_archivo = Column(String(500), nullable=False)
    hash_archivo = Column(String(64), nullable=False, unique=True, index=True)
    estado_procesamiento = Column(String(20), nullable=False, default="pendiente")
    activo = Column(Boolean, nullable=False, default=True)
    fecha_carga = Column(DateTime, nullable=False, default=datetime.utcnow)

    fragmentos = relationship(
        "FragmentoFarmacologico",
        back_populates="documento",
        cascade="all, delete-orphan",
    )
