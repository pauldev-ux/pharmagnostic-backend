from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

SIN_INFORMACION = "No se encontró información farmacológica suficiente en la base documental."


class DocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_documento: int
    titulo: str
    tipo_documento: Optional[str] = None
    fuente: Optional[str] = None
    version: Optional[str] = None
    nombre_archivo: str
    hash_archivo: str
    estado_procesamiento: str
    activo: bool
    fecha_carga: datetime
    total_fragmentos: int = 0


class DocumentoStatusUpdate(BaseModel):
    activo: bool


class ProcessResult(BaseModel):
    id_documento: int
    estado_procesamiento: str
    fragmentos_creados: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class FragmentoResultado(BaseModel):
    id_fragmento: int
    id_documento: int
    documento: str
    fuente: Optional[str] = None
    version: Optional[str] = None
    numero_fragmento: int
    contenido: str
    similitud: float


class FuenteResumen(BaseModel):
    id_documento: int
    documento: str
    fuente: Optional[str] = None
    version: Optional[str] = None


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class AskResponse(BaseModel):
    respuesta: str
    suficiente: bool
    fuentes: list[FuenteResumen] = []
    fragmentos: list[FragmentoResultado] = []
