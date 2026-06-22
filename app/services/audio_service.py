import logging
import os
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audio_clinico import AudioClinico
from app.models.user import User
from app.repositories.audio_repository import AudioRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.services import transcription

logger = logging.getLogger(__name__)
settings = get_settings()


class AudioService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AudioRepository(db)
        self.prescription_repository = PrescriptionRepository(db)

    @property
    def _allowed_formats(self) -> set[str]:
        return {f.strip().lower() for f in settings.AUDIO_ALLOWED_FORMATS.split(",") if f.strip()}

    def _ensure_recipe(self, recipe_id: int):
        recipe = self.prescription_repository.get_by_id(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        return recipe

    @staticmethod
    def _resolve_format(file: UploadFile) -> str:
        name = (file.filename or "").lower()
        if "." in name:
            return name.rsplit(".", 1)[1]
        content_type = (file.content_type or "").lower()
        return content_type.split("/")[-1] if "/" in content_type else ""

    def list_for_recipe(self, recipe_id: int) -> list[AudioClinico]:
        self._ensure_recipe(recipe_id)
        return self.repository.get_by_recipe(recipe_id)

    def get_audio(self, audio_id: int) -> AudioClinico:
        audio = self.repository.get_by_id(audio_id)
        if not audio:
            raise HTTPException(status_code=404, detail="Audio no encontrado")
        return audio

    def create_audio(
        self,
        recipe_id: int,
        file: UploadFile,
        duracion_segundos: int | None,
        current_user: User,
    ) -> AudioClinico:
        self._ensure_recipe(recipe_id)

        formato = self._resolve_format(file)
        if formato not in self._allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Formato de audio no permitido: '{formato or 'desconocido'}'. "
                f"Permitidos: {sorted(self._allowed_formats)}",
            )

        # Almacenamiento local (desarrollo).
        os.makedirs(settings.AUDIO_STORAGE_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.{formato}"
        full_path = os.path.join(settings.AUDIO_STORAGE_DIR, filename)
        content = file.file.read()
        if not content:
            raise HTTPException(status_code=400, detail="El archivo de audio está vacío")
        with open(full_path, "wb") as out:
            out.write(content)

        ruta_relativa = os.path.join(settings.AUDIO_STORAGE_DIR, filename).replace("\\", "/")
        audio = AudioClinico(
            id_receta=recipe_id,
            id_usuario=current_user.id_usuario,
            ruta_archivo=ruta_relativa,
            formato=formato,
            duracion_segundos=duracion_segundos,
            estado_procesamiento="pendiente",
        )
        return self.repository.create(audio)

    def transcribe(self, audio_id: int, current_user: User) -> AudioClinico:
        audio = self.get_audio(audio_id)

        audio.estado_procesamiento = "procesando"
        self.repository.save(audio)

        try:
            texto = transcription.transcribe_file(audio.ruta_archivo)
        except Exception as exc:  # incluye faster-whisper ausente o fallo del modelo
            logger.error("Error al transcribir el audio %s: %s", audio_id, exc)
            audio.estado_procesamiento = "error"
            self.repository.save(audio)
            raise HTTPException(status_code=500, detail="No se pudo transcribir el audio")

        audio.transcripcion = texto
        audio.estado_procesamiento = "completado"
        return self.repository.save(audio)

    def delete_audio(self, audio_id: int, current_user: User) -> None:
        audio = self.get_audio(audio_id)
        # Eliminar el archivo físico si existe (los audios sí permiten borrado físico).
        try:
            if audio.ruta_archivo and os.path.exists(audio.ruta_archivo):
                os.remove(audio.ruta_archivo)
        except OSError as exc:
            logger.warning("No se pudo eliminar el archivo %s: %s", audio.ruta_archivo, exc)
        self.repository.delete(audio)
