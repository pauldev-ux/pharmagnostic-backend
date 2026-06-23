import hashlib
import logging
import math
import os
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.documento_farmacologico import DocumentoFarmacologico
from app.models.fragmento_farmacologico import FragmentoFarmacologico
from app.repositories.pharmacological_repository import PharmacologicalRepository
from app.schemas.pharmacological import SIN_INFORMACION
from app.services import auditoria_service, ollama_client
from app.services.ollama_client import OllamaError
from app.services.text_extraction import extract_text

logger = logging.getLogger(__name__)
settings = get_settings()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    step = max(1, size - overlap)
    chunks: list[str] = []
    start = 0
    while start < len(text):
        piece = text[start : start + size].strip()
        if piece:
            chunks.append(piece)
        start += step
    return chunks


class RagService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PharmacologicalRepository(db)

    @property
    def _allowed_formats(self) -> set[str]:
        return {f.strip().lower() for f in settings.PHARMACOLOGICAL_ALLOWED_FORMATS.split(",") if f.strip()}

    @staticmethod
    def _extension(filename: str | None) -> str:
        name = (filename or "").lower()
        return name.rsplit(".", 1)[1] if "." in name else ""

    def list_documents(self) -> list[dict]:
        documentos = self.repository.list_documents()
        result = []
        for doc in documentos:
            data = doc.__dict__.copy()
            data["total_fragmentos"] = self.repository.count_fragments(doc.id_documento)
            result.append(data)
        return result

    def get_document(self, document_id: int) -> DocumentoFarmacologico:
        doc = self.repository.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        return doc

    def upload_document(
        self,
        file: UploadFile,
        titulo: str | None,
        tipo_documento: str | None,
        fuente: str | None,
        version: str | None,
        current_user=None,
    ) -> dict:
        extension = self._extension(file.filename)
        if extension not in self._allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Formato no permitido: '{extension or 'desconocido'}'. "
                f"Permitidos: {sorted(self._allowed_formats)}",
            )

        content = file.file.read()
        if not content:
            raise HTTPException(status_code=400, detail="El archivo está vacío")

        file_hash = hashlib.sha256(content).hexdigest()
        if self.repository.get_document_by_hash(file_hash):
            raise HTTPException(status_code=409, detail="El documento ya existe (hash duplicado)")

        os.makedirs(settings.PHARMACOLOGICAL_FILES_PATH, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}.{extension}"
        full_path = os.path.join(settings.PHARMACOLOGICAL_FILES_PATH, stored_name)
        with open(full_path, "wb") as out:
            out.write(content)

        documento = DocumentoFarmacologico(
            titulo=titulo or file.filename or stored_name,
            tipo_documento=tipo_documento,
            fuente=fuente,
            version=version,
            nombre_archivo=file.filename or stored_name,
            ruta_archivo=full_path.replace("\\", "/"),
            hash_archivo=file_hash,
            estado_procesamiento="pendiente",
            activo=True,
        )
        self.repository.create_document(documento)
        # Capturar la respuesta antes de auditar (el commit de auditoría expira el objeto).
        data = documento.__dict__.copy()
        data["total_fragmentos"] = 0
        auditoria_service.registrar(
            self.db, accion="documento_cargado", modulo="farmacologia",
            tabla_afectada="documento_farmacologico", id_registro=data["id_documento"],
            detalle=f"Documento '{data['titulo']}' cargado",
            user_id=current_user.id_usuario if current_user else None, commit=True,
        )
        return data

    def process_document(self, document_id: int) -> dict:
        documento = self.get_document(document_id)

        # Crear carpeta de almacenamiento si no existe
        os.makedirs(settings.PHARMACOLOGICAL_FILES_PATH, exist_ok=True)

        if not documento.ruta_archivo or not os.path.exists(documento.ruta_archivo):
            documento.estado_procesamiento = "error"
            self.repository.save(documento)
            raise HTTPException(status_code=404, detail="El archivo del documento no existe en el almacenamiento")

        documento.estado_procesamiento = "procesando"
        self.repository.save(documento)

        try:
            extension = self._extension(documento.nombre_archivo)
            texto = extract_text(documento.ruta_archivo, extension)
            fragmentos_texto = _chunk_text(texto, settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP)
            if not fragmentos_texto:
                raise HTTPException(status_code=400, detail="El documento no contiene texto procesable")

            embeddings = ollama_client.embed_texts(fragmentos_texto)

            # Re-procesar es idempotente: se eliminan los fragmentos previos.
            self.repository.delete_fragments(document_id)
            fragmentos = [
                FragmentoFarmacologico(
                    id_documento=document_id,
                    contenido=contenido,
                    numero_fragmento=indice,
                    metadatos={
                        "titulo": documento.titulo,
                        "fuente": documento.fuente,
                        "version": documento.version,
                        "numero_fragmento": indice,
                    },
                    embedding=embedding,
                )
                for indice, (contenido, embedding) in enumerate(zip(fragmentos_texto, embeddings))
            ]
            self.repository.add_fragments(fragmentos)
            documento.estado_procesamiento = "procesado"
            self.db.commit()
        except HTTPException:
            documento.estado_procesamiento = "error"
            self.repository.save(documento)
            raise
        except OllamaError:
            documento.estado_procesamiento = "error"
            self.repository.save(documento)
            raise HTTPException(status_code=503, detail="Ollama no disponible para generar embeddings")
        except Exception as exc:  # noqa: BLE001
            logger.error("Error procesando documento %s: %s", document_id, exc)
            documento.estado_procesamiento = "error"
            self.repository.save(documento)
            raise HTTPException(status_code=500, detail="Error al procesar el documento")

        return {
            "id_documento": document_id,
            "estado_procesamiento": documento.estado_procesamiento,
            "fragmentos_creados": self.repository.count_fragments(document_id),
        }

    def set_status(self, document_id: int, activo: bool) -> DocumentoFarmacologico:
        documento = self.get_document(document_id)
        documento.activo = activo
        return self.repository.save(documento)

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        import time

        inicio = time.perf_counter()
        k = top_k or settings.RAG_TOP_K
        fragmentos = self.repository.get_active_fragments()
        if not fragmentos:
            return []

        try:
            query_vec = ollama_client.embed_text(query)
        except OllamaError:
            raise HTTPException(status_code=503, detail="Ollama no disponible para la búsqueda")

        scored = []
        for fragmento in fragmentos:
            similitud = _cosine(query_vec, fragmento.embedding or [])
            scored.append((similitud, fragmento))
        scored.sort(key=lambda item: item[0], reverse=True)

        resultados = []
        for similitud, fragmento in scored[:k]:
            doc = fragmento.documento
            resultados.append(
                {
                    "id_fragmento": fragmento.id_fragmento,
                    "id_documento": fragmento.id_documento,
                    "documento": doc.titulo if doc else "",
                    "fuente": doc.fuente if doc else None,
                    "version": doc.version if doc else None,
                    "numero_fragmento": fragmento.numero_fragmento,
                    "contenido": fragmento.contenido,
                    "similitud": round(float(similitud), 4),
                }
            )
        logger.info(
            "Búsqueda RAG: %d fragmentos evaluados en %d ms", len(fragmentos), int((time.perf_counter() - inicio) * 1000)
        )
        return resultados

    def ask(self, query: str, top_k: int | None = None) -> dict:
        resultados = self.search(query, top_k)
        suficientes = [r for r in resultados if r["similitud"] >= settings.RAG_MIN_SIMILARITY]

        if not suficientes:
            return {
                "respuesta": SIN_INFORMACION,
                "suficiente": False,
                "fuentes": [],
                "fragmentos": [],
            }

        contexto = "\n\n".join(
            f"[Documento: {r['documento']} | Fuente: {r['fuente'] or 'N/D'} | "
            f"Versión: {r['version'] or 'N/D'}]\n{r['contenido']}"
            for r in suficientes
        )
        system = (
            "Eres un asistente farmacológico. Responde ÚNICAMENTE con la información del CONTEXTO. "
            "No inventes datos ni uses conocimiento externo. Si el contexto no contiene información "
            f"suficiente, responde exactamente: '{SIN_INFORMACION}'. Cita las fuentes del contexto."
        )
        prompt = f"CONTEXTO:\n{contexto}\n\nPREGUNTA: {query}\n\nRespuesta basada solo en el contexto:"

        try:
            respuesta = ollama_client.chat(system, prompt)
        except OllamaError:
            raise HTTPException(status_code=503, detail="Ollama no disponible para responder")

        fuentes_vistas: dict[int, dict] = {}
        for r in suficientes:
            fuentes_vistas.setdefault(
                r["id_documento"],
                {
                    "id_documento": r["id_documento"],
                    "documento": r["documento"],
                    "fuente": r["fuente"],
                    "version": r["version"],
                },
            )

        return {
            "respuesta": respuesta,
            "suficiente": True,
            "fuentes": list(fuentes_vistas.values()),
            "fragmentos": suficientes,
        }
