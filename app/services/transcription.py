"""Transcripción de audio con Faster-Whisper.

El modelo se carga de forma perezosa (solo al transcribir por primera vez) y es
configurable por variable de entorno (`WHISPER_MODEL`). De este modo la aplicación
arranca aunque la dependencia o el modelo aún no estén disponibles, y las pruebas
pueden sustituir `transcribe_file` por un mock.
"""

import logging
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def _get_model():
    # Import perezoso para no exigir faster-whisper en el arranque/tests.
    from faster_whisper import WhisperModel

    logger.info("Cargando modelo Whisper '%s'", settings.WHISPER_MODEL)
    return WhisperModel(
        settings.WHISPER_MODEL,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )


def transcribe_file(path: str) -> str:
    """Devuelve el texto transcrito del archivo de audio indicado."""
    model = _get_model()
    segments, _info = model.transcribe(path)
    return " ".join(segment.text.strip() for segment in segments).strip()
