import random

from app.services import transcription
from tests.conftest import requires_db

pytestmark = requires_db


def _ci() -> str:
    return f"CI{random.randint(10_000_000, 99_999_999)}"


def _create_patient(client, doctor_headers) -> int:
    res = client.post(
        "/api/v1/patients",
        headers=doctor_headers,
        json={"nombre": "Aud", "apellido": "Test", "ci": _ci(), "fecha_nacimiento": "1990-01-01"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id_paciente"]


def _create_medication(client, auth_headers, nombre: str) -> int:
    res = client.post("/api/v1/medications", headers=auth_headers, json={"nombre": nombre})
    assert res.status_code == 201, res.text
    return res.json()["id_medicamento"]


def _create_recipe(client, doctor_headers, patient_id: int, items: list[dict]) -> dict:
    res = client.post(
        "/api/v1/prescriptions",
        headers=doctor_headers,
        json={"id_paciente": patient_id, "items": items},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _audio_file(content: bytes = b"fake-audio-bytes", name: str = "grabacion.webm", mime: str = "audio/webm"):
    return {"file": (name, content, mime)}


# --- Audio clínico --------------------------------------------------------------

def test_subida_de_audio(client, doctor_headers, auth_headers):
    pid = _create_patient(client, doctor_headers)
    med = _create_medication(client, auth_headers, f"Paracetamol {random.randint(1,9999)}")
    recipe = _create_recipe(client, doctor_headers, pid, [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h"}])

    res = client.post(
        f"/api/v1/prescriptions/{recipe['id_receta']}/audios",
        headers=doctor_headers,
        files=_audio_file(),
        data={"duracion_segundos": "7"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["estado_procesamiento"] == "pendiente"
    assert body["formato"] == "webm"
    assert body["duracion_segundos"] == 7


def test_formato_no_permitido(client, doctor_headers, auth_headers):
    pid = _create_patient(client, doctor_headers)
    med = _create_medication(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _create_recipe(client, doctor_headers, pid, [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h"}])
    res = client.post(
        f"/api/v1/prescriptions/{recipe['id_receta']}/audios",
        headers=doctor_headers,
        files={"file": ("nota.txt", b"hola", "text/plain")},
    )
    assert res.status_code == 400


def test_audio_receta_inexistente(client, doctor_headers):
    res = client.post(
        "/api/v1/prescriptions/999999/audios", headers=doctor_headers, files=_audio_file()
    )
    assert res.status_code == 404


def test_audio_permisos_por_rol(client, doctor_headers, auth_headers, pharmacist_headers):
    pid = _create_patient(client, doctor_headers)
    med = _create_medication(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _create_recipe(client, doctor_headers, pid, [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h"}])
    rid = recipe["id_receta"]

    # El admin (superusuario) sí puede grabar; el farmacéutico no.
    assert client.post(f"/api/v1/prescriptions/{rid}/audios", headers=auth_headers, files=_audio_file()).status_code == 201
    assert (
        client.post(f"/api/v1/prescriptions/{rid}/audios", headers=pharmacist_headers, files=_audio_file()).status_code
        == 403
    )
    # Admin sí puede consultar (lectura).
    assert client.get(f"/api/v1/prescriptions/{rid}/audios", headers=auth_headers).status_code == 200
    # Farmacéutico no accede a la lectura de audios.
    assert client.get(f"/api/v1/prescriptions/{rid}/audios", headers=pharmacist_headers).status_code == 403


def _upload_audio(client, doctor_headers, auth_headers) -> int:
    pid = _create_patient(client, doctor_headers)
    med = _create_medication(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _create_recipe(client, doctor_headers, pid, [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h"}])
    res = client.post(
        f"/api/v1/prescriptions/{recipe['id_receta']}/audios", headers=doctor_headers, files=_audio_file()
    )
    return res.json()["id_audio"]


def test_transcripcion(client, doctor_headers, auth_headers, monkeypatch):
    audio_id = _upload_audio(client, doctor_headers, auth_headers)
    monkeypatch.setattr(transcription, "transcribe_file", lambda path: "tomar paracetamol cada ocho horas")

    res = client.post(f"/api/v1/audios/{audio_id}/transcribe", headers=doctor_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["estado_procesamiento"] == "completado"
    assert "paracetamol" in body["transcripcion"].lower()


def test_error_de_whisper(client, doctor_headers, auth_headers, monkeypatch):
    audio_id = _upload_audio(client, doctor_headers, auth_headers)

    def _boom(path):
        raise RuntimeError("modelo no disponible")

    monkeypatch.setattr(transcription, "transcribe_file", _boom)
    res = client.post(f"/api/v1/audios/{audio_id}/transcribe", headers=doctor_headers)
    assert res.status_code == 500
    # El audio queda marcado con estado 'error'.
    estado = client.get(f"/api/v1/audios/{audio_id}", headers=doctor_headers).json()["estado_procesamiento"]
    assert estado == "error"


def test_eliminar_audio(client, doctor_headers, auth_headers):
    audio_id = _upload_audio(client, doctor_headers, auth_headers)
    assert client.delete(f"/api/v1/audios/{audio_id}", headers=doctor_headers).status_code == 204
    assert client.get(f"/api/v1/audios/{audio_id}", headers=doctor_headers).status_code == 404


# --- Alertas / prevalidación ----------------------------------------------------

def test_prevalidacion_sin_alertas(client, doctor_headers, auth_headers):
    pid = _create_patient(client, doctor_headers)
    med = _create_medication(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _create_recipe(client, doctor_headers, pid, [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h"}])

    res = client.post(f"/api/v1/prescriptions/{recipe['id_receta']}/prevalidate", headers=doctor_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["nivel_maximo"] == 0
    assert body["total_alertas"] == 0
    assert "No reemplaza la revisión médica" in body["mensaje"]


def test_prevalidacion_campos_incompletos(client, doctor_headers, auth_headers):
    pid = _create_patient(client, doctor_headers)
    med = _create_medication(client, auth_headers, f"Med {random.randint(1,9999)}")
    # Ítem sin dosis ni frecuencia => nivel 1.
    recipe = _create_recipe(client, doctor_headers, pid, [{"id_medicamento": med}])

    res = client.post(f"/api/v1/prescriptions/{recipe['id_receta']}/prevalidate", headers=doctor_headers)
    body = res.json()
    assert body["nivel_maximo"] == 1
    assert any(a["tipo_alerta"] == "campos_incompletos" and a["nivel"] == 1 for a in body["alertas"])


def test_prevalidacion_medicamento_duplicado(client, doctor_headers, auth_headers):
    pid = _create_patient(client, doctor_headers)
    med = _create_medication(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _create_recipe(
        client,
        doctor_headers,
        pid,
        [
            {"id_medicamento": med, "dosis": "1", "frecuencia": "8h"},
            {"id_medicamento": med, "dosis": "1", "frecuencia": "12h"},
        ],
    )
    res = client.post(f"/api/v1/prescriptions/{recipe['id_receta']}/prevalidate", headers=doctor_headers)
    body = res.json()
    assert body["nivel_maximo"] == 2
    assert any(a["tipo_alerta"] == "medicamento_duplicado" and a["nivel"] == 2 for a in body["alertas"])


def test_prevalidacion_reemplaza_anteriores(client, doctor_headers, auth_headers):
    pid = _create_patient(client, doctor_headers)
    med = _create_medication(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _create_recipe(client, doctor_headers, pid, [{"id_medicamento": med}])
    rid = recipe["id_receta"]
    client.post(f"/api/v1/prescriptions/{rid}/prevalidate", headers=doctor_headers)
    # Segunda corrida: no debe acumular alertas duplicadas.
    res = client.post(f"/api/v1/prescriptions/{rid}/prevalidate", headers=doctor_headers)
    assert res.json()["total_alertas"] == len(
        client.get(f"/api/v1/prescriptions/{rid}/alerts", headers=doctor_headers).json()
    )


def test_listado_y_revision_de_alertas(client, doctor_headers, auth_headers):
    pid = _create_patient(client, doctor_headers)
    med = _create_medication(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _create_recipe(client, doctor_headers, pid, [{"id_medicamento": med}])
    rid = recipe["id_receta"]
    client.post(f"/api/v1/prescriptions/{rid}/prevalidate", headers=doctor_headers)

    # Listado (admin puede consultar).
    listado = client.get(f"/api/v1/prescriptions/{rid}/alerts", headers=auth_headers)
    assert listado.status_code == 200 and len(listado.json()) >= 1
    alerta_id = listado.json()[0]["id_alerta"]

    # Revisión: médico y admin (superusuario) pueden.
    assert client.patch(f"/api/v1/alerts/{alerta_id}/review", headers=auth_headers, json={"revisada": True}).status_code == 200
    rev = client.patch(f"/api/v1/alerts/{alerta_id}/review", headers=doctor_headers, json={"revisada": True})
    assert rev.status_code == 200 and rev.json()["revisada"] is True


def test_prevalidacion_permisos(client, doctor_headers, auth_headers, pharmacist_headers):
    pid = _create_patient(client, doctor_headers)
    med = _create_medication(client, auth_headers, f"Med {random.randint(1,9999)}")
    recipe = _create_recipe(client, doctor_headers, pid, [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h"}])
    rid = recipe["id_receta"]
    # El admin (superusuario) sí prevalida; el farmacéutico no.
    assert client.post(f"/api/v1/prescriptions/{rid}/prevalidate", headers=auth_headers).status_code == 200
    assert client.post(f"/api/v1/prescriptions/{rid}/prevalidate", headers=pharmacist_headers).status_code == 403
