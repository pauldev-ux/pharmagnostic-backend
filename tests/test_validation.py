import json
import random

from app.services import ollama_client
from app.services import validation_service as vs_module
from tests.conftest import requires_db

pytestmark = requires_db

VALID_JSON = json.dumps(
    {
        "resumen": "Análisis de apoyo basado en el contexto.",
        "interacciones": [],
        "contraindicaciones": [],
        "nivel_sugerido": 0,
    }
)


def _mock_llm(monkeypatch, chat_return=VALID_JSON):
    # Mockea Ollama (embeddings + chat) para no depender de la red ni del servidor.
    monkeypatch.setattr(ollama_client, "embed_text", lambda t: [0.1] * 8)
    monkeypatch.setattr(ollama_client, "embed_texts", lambda ts: [[0.1] * 8 for _ in ts])
    monkeypatch.setattr(ollama_client, "chat", lambda system, prompt: chat_return)


def _ci() -> str:
    return f"CI{random.randint(10_000_000, 99_999_999)}"


def _patient(client, doctor_headers, **over) -> int:
    payload = {"nombre": "Val", "apellido": "Test", "ci": _ci(), "fecha_nacimiento": "1990-01-01"}
    payload.update(over)
    r = client.post("/api/v1/patients", headers=doctor_headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()["id_paciente"]


def _med(client, auth_headers, nombre) -> int:
    r = client.post("/api/v1/medications", headers=auth_headers, json={"nombre": nombre})
    assert r.status_code == 201, r.text
    return r.json()["id_medicamento"]


def _recipe(client, doctor_headers, patient_id, items, id_diagnostico=None) -> dict:
    body = {"id_paciente": patient_id, "items": items}
    if id_diagnostico:
        body["id_diagnostico"] = id_diagnostico
    r = client.post("/api/v1/prescriptions", headers=doctor_headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _diagnosis(client, doctor_headers, patient_id) -> int:
    r = client.post(
        f"/api/v1/patients/{patient_id}/diagnoses",
        headers=doctor_headers,
        json={"descripcion": "Dx de prueba"},
    )
    return r.json()["id_diagnostico"]


# --- Validación general ---------------------------------------------------------

def test_validar_receta_basica(client, doctor_headers, auth_headers, monkeypatch):
    _mock_llm(monkeypatch)
    pid = _patient(client, doctor_headers)
    did = _diagnosis(client, doctor_headers, pid)
    med = _med(client, auth_headers, f"Paracetamol {random.randint(1,9999)}")
    recipe = _recipe(
        client, doctor_headers, pid,
        [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h", "instrucciones": "oral 3 días"}],
        id_diagnostico=did,
    )
    res = client.post(f"/api/v1/prescriptions/{recipe['id_receta']}/validate", headers=doctor_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["nivel_riesgo"] == 0
    assert body["bloqueada"] is False
    assert "no sustituye el criterio médico" in body["mensaje"]


def test_validar_duplicidad(client, doctor_headers, auth_headers, monkeypatch):
    _mock_llm(monkeypatch)
    pid = _patient(client, doctor_headers)
    med = _med(client, auth_headers, f"Ibuprofeno {random.randint(1,9999)}")
    recipe = _recipe(
        client, doctor_headers, pid,
        [
            {"id_medicamento": med, "dosis": "1", "frecuencia": "8h", "instrucciones": "oral"},
            {"id_medicamento": med, "dosis": "1", "frecuencia": "12h", "instrucciones": "oral"},
        ],
        id_diagnostico=_diagnosis(client, doctor_headers, pid),
    )
    body = client.post(f"/api/v1/prescriptions/{recipe['id_receta']}/validate", headers=doctor_headers).json()
    assert any(d["medicamento"] for d in body["duplicidades"])
    assert body["nivel_riesgo"] >= 2


def test_validar_alergia_bloquea(client, doctor_headers, auth_headers, monkeypatch):
    _mock_llm(monkeypatch)
    nombre_med = f"Amoxicilina{random.randint(1,9999)}"
    pid = _patient(client, doctor_headers, alergias=nombre_med.lower())
    med = _med(client, auth_headers, nombre_med)
    recipe = _recipe(
        client, doctor_headers, pid,
        [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h", "instrucciones": "oral"}],
        id_diagnostico=_diagnosis(client, doctor_headers, pid),
    )
    rid = recipe["id_receta"]
    body = client.post(f"/api/v1/prescriptions/{rid}/validate", headers=doctor_headers).json()
    assert body["nivel_riesgo"] == 3
    assert body["bloqueada"] is True
    assert any(c.get("medicamento") for c in body["contraindicaciones"])

    # La receta queda bloqueada.
    receta = client.get(f"/api/v1/prescriptions/{rid}", headers=doctor_headers).json()
    assert receta["bloqueada"] is True

    # Justificar la desbloquea.
    just = client.patch(
        f"/api/v1/prescriptions/{rid}/justify", headers=doctor_headers, json={"justificacion": "Riesgo asumido y monitorizado."}
    )
    assert just.status_code == 200 and just.json()["bloqueada"] is False
    assert client.get(f"/api/v1/prescriptions/{rid}", headers=doctor_headers).json()["bloqueada"] is False


def test_validar_dosis_incompleta(client, doctor_headers, auth_headers, monkeypatch):
    _mock_llm(monkeypatch)
    pid = _patient(client, doctor_headers)
    med = _med(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _recipe(
        client, doctor_headers, pid, [{"id_medicamento": med}],  # sin dosis/frecuencia/instrucciones
        id_diagnostico=_diagnosis(client, doctor_headers, pid),
    )
    body = client.post(f"/api/v1/prescriptions/{recipe['id_receta']}/validate", headers=doctor_headers).json()
    assert len(body["errores_dosis"]) >= 1
    assert body["nivel_riesgo"] >= 1


def test_validar_inconsistencia_audio(client, doctor_headers, auth_headers, monkeypatch):
    _mock_llm(monkeypatch)
    pid = _patient(client, doctor_headers)
    nombre = f"Loratadina{random.randint(1,9999)}"
    med = _med(client, auth_headers, nombre)
    recipe = _recipe(
        client, doctor_headers, pid,
        [{"id_medicamento": med, "dosis": "1", "frecuencia": "24h", "instrucciones": "oral"}],
        id_diagnostico=_diagnosis(client, doctor_headers, pid),
    )
    rid = recipe["id_receta"]
    # Subir un audio y transcribirlo con un texto que NO menciona el medicamento.
    up = client.post(f"/api/v1/prescriptions/{rid}/audios", headers=doctor_headers, files={"file": ("a.webm", b"bytes", "audio/webm")})
    aid = up.json()["id_audio"]
    from app.services import transcription
    monkeypatch.setattr(transcription, "transcribe_file", lambda path: "tomar otro farmaco distinto cada dia")
    client.post(f"/api/v1/audios/{aid}/transcribe", headers=doctor_headers)

    body = client.post(f"/api/v1/prescriptions/{rid}/validate", headers=doctor_headers).json()
    assert len(body["inconsistencias_audio"]) >= 1
    assert body["id_audio"] == aid


def test_validar_respuesta_invalida_de_ollama(client, doctor_headers, auth_headers, monkeypatch):
    _mock_llm(monkeypatch, chat_return="esto no es json válido")
    pid = _patient(client, doctor_headers)
    med = _med(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _recipe(
        client, doctor_headers, pid,
        [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h", "instrucciones": "oral"}],
        id_diagnostico=_diagnosis(client, doctor_headers, pid),
    )
    res = client.post(f"/api/v1/prescriptions/{recipe['id_receta']}/validate", headers=doctor_headers)
    assert res.status_code == 502


def test_permisos_validacion(client, doctor_headers, auth_headers, pharmacist_headers, monkeypatch):
    _mock_llm(monkeypatch)
    pid = _patient(client, doctor_headers)
    med = _med(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _recipe(
        client, doctor_headers, pid,
        [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h", "instrucciones": "oral"}],
        id_diagnostico=_diagnosis(client, doctor_headers, pid),
    )
    rid = recipe["id_receta"]
    # Validar el primero (médico) para tener historial.
    client.post(f"/api/v1/prescriptions/{rid}/validate", headers=doctor_headers)

    # El admin (superusuario) también valida; el farmacéutico no.
    assert client.post(f"/api/v1/prescriptions/{rid}/validate", headers=auth_headers).status_code == 200
    assert client.post(f"/api/v1/prescriptions/{rid}/validate", headers=pharmacist_headers).status_code == 403
    assert client.get(f"/api/v1/prescriptions/{rid}/validations", headers=auth_headers).status_code == 200
    assert client.get(f"/api/v1/prescriptions/{rid}/validations", headers=pharmacist_headers).status_code == 403
