"""Cliente ligero para Ollama (embeddings con nomic-embed-text y chat con Llama 3).

Se comunica con la API REST de Ollama vía httpx. Las funciones son fáciles de
sustituir por mocks en las pruebas (no requieren Ollama en marcha).
"""

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaError(RuntimeError):
    """Error de comunicación con Ollama."""


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Genera un embedding por cada texto usando el modelo de embeddings configurado."""
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
    vectors: list[list[float]] = []
    try:
        with httpx.Client(timeout=120) as client:
            for text in texts:
                resp = client.post(
                    url, json={"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": text}
                )
                resp.raise_for_status()
                vectors.append(resp.json()["embedding"])
    except Exception as exc:  # noqa: BLE001
        logger.error("Error generando embeddings con Ollama: %s", exc)
        raise OllamaError("No se pudieron generar los embeddings con Ollama") from exc
    return vectors


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def chat(system: str, prompt: str) -> str:
    """Genera una respuesta con el modelo de chat configurado (Llama 3)."""
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    try:
        with httpx.Client(timeout=180) as client:
            resp = client.post(
                url,
                json={
                    "model": settings.OLLAMA_CHAT_MODEL,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        logger.error("Error consultando el chat de Ollama: %s", exc)
        raise OllamaError("No se pudo obtener respuesta del modelo de chat") from exc
