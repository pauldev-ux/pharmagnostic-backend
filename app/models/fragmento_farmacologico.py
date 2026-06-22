from sqlalchemy import ARRAY, Column, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class FragmentoFarmacologico(Base):
    __tablename__ = "fragmento_farmacologico"

    id_fragmento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_documento = Column(
        Integer, ForeignKey("documento_farmacologico.id_documento"), nullable=False, index=True
    )
    contenido = Column(Text, nullable=False)
    numero_fragmento = Column(Integer, nullable=False, default=0)
    # Atributo Python 'metadatos' mapeado a la columna 'metadata' (reservada por SQLAlchemy).
    metadatos = Column("metadata", JSONB, nullable=True)
    # Embedding portátil (double precision[]). Listo para migrar a pgvector si la
    # extensión está disponible; la similitud coseno se calcula en la capa de servicio.
    embedding = Column(ARRAY(Float), nullable=True)

    documento = relationship("DocumentoFarmacologico", back_populates="fragmentos")
