import hashlib
import random
import re

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.schemas.pharmacological import SIN_INFORMACION
from app.services import ollama_client
from app.services.ollama_client import OllamaError
from tests.conftest import requires_db

pytestmark = requires_db

DIM = 64


def _fake_vector(texto: str) -> list[float]:
    """Embedding determinista tipo bag-of-words (offline, sin Ollama)."""
    vec = [0.0] * DIM
    for palabra in re.findall(r"[a-záéíóúñ0-9]+", texto.lower()):
        idx = int(hashlib.md5(palabra.encode()).hexdigest(), 16) % DIM
        vec[idx] += 1.0
    return vec


def _fake_embed_texts(textos: list[str]) -> list[list[float]]:
    return [_fake_vector(t) for t in textos]


def _mock_embeddings(monkeypatch):
    monkeypatch.setattr(ollama_client, "embed_texts", _fake_embed_texts)
    monkeypatch.setattr(ollama_client, "embed_text", lambda t: _fake_vector(t))


@pytest.fixture(scope="module", autouse=True)
def _clean_pharma():
    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM fragmento_farmacologico"))
        db.execute(text("DELETE FROM documento_farmacologico"))
        db.commit()
    finally:
        db.close()


def _upload_txt(client, admin_headers, contenido: str, titulo="Vademécum", fuente="OMS", version="2024"):
    res = client.post(
        "/api/v1/pharmacological-documents",
        headers=admin_headers,
        files={"file": (f"{titulo}.txt", contenido.encode("utf-8"), "text/plain")},
        data={"titulo": titulo, "tipo_documento": "vademecum", "fuente": fuente, "version": version},
    )
    return res


# --- Carga de documentos --------------------------------------------------------

def test_ask_sin_informacion(client, auth_headers):
    # Sin documentos procesados, ask responde el mensaje fijo y no es suficiente.
    res = client.post(
        "/api/v1/pharmacological-knowledge/ask",
        headers=auth_headers,
        json={"query": "dosis de paracetamol"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["suficiente"] is False
    assert body["respuesta"] == SIN_INFORMACION
    assert body["fragmentos"] == []


def test_upload_formato_no_permitido(client, auth_headers):
    res = client.post(
        "/api/v1/pharmacological-documents",
        headers=auth_headers,
        files={"file": ("malware.exe", b"binario", "application/octet-stream")},
    )
    assert res.status_code == 400


def test_upload_y_duplicado(client, auth_headers):
    contenido = f"Contenido unico {random.randint(1, 10_000_000)} sobre medicamentos."
    primero = _upload_txt(client, auth_headers, contenido)
    assert primero.status_code == 201, primero.text
    assert primero.json()["estado_procesamiento"] == "pendiente"
    # Mismo contenido => mismo hash => duplicado.
    segundo = _upload_txt(client, auth_headers, contenido)
    assert segundo.status_code == 409


def test_permisos(client, auth_headers, doctor_headers, pharmacist_headers):
    contenido = f"Texto {random.randint(1, 10_000_000)}"
    # Médico y farmacéutico NO pueden cargar.
    assert _upload_txt(client, doctor_headers, contenido).status_code == 403
    assert _upload_txt(client, pharmacist_headers, contenido).status_code == 403
    # Médico y farmacéutico SÍ pueden consultar/buscar.
    assert client.post("/api/v1/pharmacological-knowledge/search", headers=doctor_headers, json={"query": "x"}).status_code == 200
    assert client.post("/api/v1/pharmacological-knowledge/search", headers=pharmacist_headers, json={"query": "x"}).status_code == 200


# --- Procesamiento, embeddings y búsqueda --------------------------------------

def test_procesar_y_buscar(client, auth_headers, monkeypatch):
    _mock_embeddings(monkeypatch)
    contenido = (
        "El paracetamol se usa para la fiebre y el dolor leve. "
        "La amoxicilina es un antibiotico para infecciones bacterianas. "
        f"Referencia {random.randint(1, 10_000_000)}."
    )
    doc = _upload_txt(client, auth_headers, contenido, titulo="GuiaClinica", fuente="MINSA", version="v3").json()

    proc = client.post(
        f"/api/v1/pharmacological-documents/{doc['id_documento']}/process", headers=auth_headers
    )
    assert proc.status_code == 200, proc.text
    assert proc.json()["estado_procesamiento"] == "procesado"
    assert proc.json()["fragmentos_creados"] >= 1

    res = client.post(
        "/api/v1/pharmacological-knowledge/search",
        headers=auth_headers,
        json={"query": "antibiotico amoxicilina infecciones", "top_k": 3},
    )
    assert res.status_code == 200, res.text
    resultados = res.json()
    assert len(resultados) >= 1
    top = resultados[0]
    assert top["similitud"] > 0
    assert top["documento"] == "GuiaClinica"
    assert top["fuente"] == "MINSA"
    assert top["version"] == "v3"
    assert "amoxicilina" in top["contenido"].lower()


def test_procesar_error_ollama(client, auth_headers, monkeypatch):
    def _boom(textos):
        raise OllamaError("ollama caído")

    monkeypatch.setattr(ollama_client, "embed_texts", _boom)
    contenido = f"Documento con error {random.randint(1, 10_000_000)}."
    doc = _upload_txt(client, auth_headers, contenido).json()
    res = client.post(
        f"/api/v1/pharmacological-documents/{doc['id_documento']}/process", headers=auth_headers
    )
    assert res.status_code == 503
    # El documento queda marcado en estado 'error'.
    lst = client.get("/api/v1/pharmacological-documents", headers=auth_headers).json()
    doc_db = next(d for d in lst if d["id_documento"] == doc["id_documento"])
    assert doc_db["estado_procesamiento"] == "error"


def test_ask_con_contexto(client, auth_headers, monkeypatch):
    _mock_embeddings(monkeypatch)
    monkeypatch.setattr(
        ollama_client, "chat", lambda system, prompt: "El ibuprofeno es un antiinflamatorio (según el contexto)."
    )
    contenido = (
        "El ibuprofeno es un antiinflamatorio no esteroideo usado para dolor e inflamacion. "
        f"Codigo {random.randint(1, 10_000_000)}."
    )
    doc = _upload_txt(client, auth_headers, contenido, titulo="Farmacologia", fuente="Fuente X", version="1.0").json()
    client.post(f"/api/v1/pharmacological-documents/{doc['id_documento']}/process", headers=auth_headers)

    res = client.post(
        "/api/v1/pharmacological-knowledge/ask",
        headers=auth_headers,
        json={"query": "para que sirve el ibuprofeno antiinflamatorio"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["suficiente"] is True
    assert "ibuprofeno" in body["respuesta"].lower()
    assert len(body["fragmentos"]) >= 1
    assert any(f["documento"] == "Farmacologia" for f in body["fuentes"])


def test_activar_desactivar_excluye_de_busqueda(client, auth_headers, monkeypatch):
    _mock_embeddings(monkeypatch)
    palabra = f"clorfenamina{random.randint(1, 10_000_000)}"
    contenido = f"La {palabra} es un antihistaminico para alergias."
    doc = _upload_txt(client, auth_headers, contenido, titulo="Antialergicos").json()
    did = doc["id_documento"]
    client.post(f"/api/v1/pharmacological-documents/{did}/process", headers=auth_headers)

    # Activo: aparece en la búsqueda.
    antes = client.post(
        "/api/v1/pharmacological-knowledge/search", headers=auth_headers, json={"query": palabra}
    ).json()
    assert any(r["id_documento"] == did for r in antes)

    # Desactivar.
    patch = client.patch(
        f"/api/v1/pharmacological-documents/{did}/status", headers=auth_headers, json={"activo": False}
    )
    assert patch.status_code == 200 and patch.json()["activo"] is False

    # Ya no aparece.
    despues = client.post(
        "/api/v1/pharmacological-knowledge/search", headers=auth_headers, json={"query": palabra}
    ).json()
    assert all(r["id_documento"] != did for r in despues)
