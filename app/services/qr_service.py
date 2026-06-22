"""Generación de códigos de verificación y QR para dispensación.

El QR contiene únicamente una URL de verificación con un token aleatorio difícil
de adivinar. No incluye datos personales, medicamentos ni información clínica.
"""

import base64
import io
import secrets

from app.core.config import get_settings

settings = get_settings()


def generate_token() -> str:
    """Token aleatorio URL-safe (≈ 256 bits) difícil de adivinar."""
    return secrets.token_urlsafe(32)


def verification_url(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/farmacia/verificar/{token}"


def generate_qr_base64(data: str) -> str:
    """Devuelve la imagen QR como data URI PNG en base64 (import perezoso)."""
    import qrcode

    img = qrcode.make(data)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def extract_token(value: str) -> str:
    """Acepta el token directo o una URL de verificación y devuelve el token."""
    value = (value or "").strip()
    if "/" in value:
        return value.rstrip("/").rsplit("/", 1)[-1]
    return value
