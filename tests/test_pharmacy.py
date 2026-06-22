import json
import random

from app.services import ollama_client
from tests.conftest import requires_db

pytestmark = requires_db

VALID_JSON = json.dumps(
    {"resumen": "ok", "interacciones": [], "contraindicaciones": [], "nivel_sugerido": 0}
)


def _mock_ollama(monkeypatch):
    monkeypatch.setattr(ollama_client, "embed_text", lambda t: [0.1] * 8)
    monkeypatch.setattr(ollama_client, "embed_texts", lambda ts: [[0.1] * 8 for _ in ts])
    monkeypatch.setattr(ollama_client, "chat", lambda system, prompt: VALID_JSON)


def _ci() -> str:
    return f"CI{random.randint(10_000_000, 99_999_999)}"


def _validated_recipe(client, doctor_headers, auth_headers, monkeypatch, alergias=None, block=False):
    """Crea una receta y la valida (queda validada). Si block=True, fuerza nivel 3."""
    _mock_ollama(monkeypatch)
    payload = {"nombre": "Far", "apellido": "Test", "ci": _ci(), "fecha_nacimiento": "1990-01-01"}
    if alergias:
        payload["alergias"] = alergias
    pid = client.post("/api/v1/patients", headers=doctor_headers, json=payload).json()["id_paciente"]
    did = client.post(f"/api/v1/patients/{pid}/diagnoses", headers=doctor_headers, json={"descripcion": "Dx"}).json()["id_diagnostico"]
    nombre_med = (alergias.split(",")[0].strip() if (block and alergias) else f"Med {random.randint(1,9999)}")
    med = client.post("/api/v1/medications", headers=auth_headers, json={"nombre": nombre_med}).json()["id_medicamento"]
    recipe = client.post(
        "/api/v1/prescriptions", headers=doctor_headers,
        json={"id_paciente": pid, "id_diagnostico": did,
              "items": [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h", "instrucciones": "oral"}]},
    ).json()
    rid = recipe["id_receta"]
    client.post(f"/api/v1/prescriptions/{rid}/validate", headers=doctor_headers)
    return rid


# --- Generación de QR -----------------------------------------------------------

def test_generar_qr(client, doctor_headers, auth_headers, monkeypatch):
    rid = _validated_recipe(client, doctor_headers, auth_headers, monkeypatch)
    res = client.post(f"/api/v1/prescriptions/{rid}/generate-qr", headers=doctor_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["estado"] == "pendiente"
    assert body["qr_base64"].startswith("data:image/png;base64,")
    assert len(body["codigo_verificacion"]) >= 20
    # El contenido del QR no debe llevar datos clínicos: solo una URL de verificación.
    assert "/farmacia/verificar/" in body["url_verificacion"]

    # No genera varios QR activos: re-generar devuelve el mismo código.
    res2 = client.post(f"/api/v1/prescriptions/{rid}/generate-qr", headers=doctor_headers)
    assert res2.json()["codigo_verificacion"] == body["codigo_verificacion"]


def test_generar_qr_requiere_validacion(client, doctor_headers, auth_headers):
    # Receta sin validar.
    pid = client.post("/api/v1/patients", headers=doctor_headers, json={"nombre": "X", "apellido": "Y", "ci": _ci(), "fecha_nacimiento": "1990-01-01"}).json()["id_paciente"]
    med = client.post("/api/v1/medications", headers=auth_headers, json={"nombre": f"Med {random.randint(1,9999)}"}).json()["id_medicamento"]
    rid = client.post("/api/v1/prescriptions", headers=doctor_headers, json={"id_paciente": pid, "items": [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h"}]}).json()["id_receta"]
    res = client.post(f"/api/v1/prescriptions/{rid}/generate-qr", headers=doctor_headers)
    assert res.status_code == 400


def test_generar_qr_receta_bloqueada(client, doctor_headers, auth_headers, monkeypatch):
    rid = _validated_recipe(client, doctor_headers, auth_headers, monkeypatch, alergias="amoxicilina", block=True)
    # Debe haber quedado bloqueada (nivel 3).
    assert client.get(f"/api/v1/prescriptions/{rid}", headers=doctor_headers).json()["bloqueada"] is True
    res = client.post(f"/api/v1/prescriptions/{rid}/generate-qr", headers=doctor_headers)
    assert res.status_code == 400


# --- Verificación ---------------------------------------------------------------

def test_verificar_qr_valido_e_invalido(client, doctor_headers, auth_headers, pharmacist_headers, monkeypatch):
    rid = _validated_recipe(client, doctor_headers, auth_headers, monkeypatch)
    codigo = client.post(f"/api/v1/prescriptions/{rid}/generate-qr", headers=doctor_headers).json()["codigo_verificacion"]

    ok = client.post("/api/v1/pharmacy/verify-qr", headers=pharmacist_headers, json={"codigo": codigo})
    assert ok.status_code == 200 and ok.json()["estado_qr"] == "valido"

    bad = client.post("/api/v1/pharmacy/verify-qr", headers=pharmacist_headers, json={"codigo": "noexiste123"})
    assert bad.json()["estado_qr"] == "invalido"


# --- Dispensación ---------------------------------------------------------------

def test_dispensacion_correcta_y_doble(client, doctor_headers, auth_headers, pharmacist_headers, monkeypatch):
    rid = _validated_recipe(client, doctor_headers, auth_headers, monkeypatch)
    codigo = client.post(f"/api/v1/prescriptions/{rid}/generate-qr", headers=doctor_headers).json()["codigo_verificacion"]

    disp = client.post(
        f"/api/v1/pharmacy/recipes/{rid}/dispense", headers=pharmacist_headers,
        json={"codigo_verificacion": codigo, "observaciones": "Entregado al paciente"},
    )
    assert disp.status_code == 200, disp.text
    assert disp.json()["estado"] == "confirmada"

    # La receta pasa a 'dispensada'.
    assert client.get(f"/api/v1/prescriptions/{rid}", headers=doctor_headers).json()["estado"] == "dispensada"

    # Doble dispensación rechazada.
    dup = client.post(f"/api/v1/pharmacy/recipes/{rid}/dispense", headers=pharmacist_headers, json={})
    assert dup.status_code == 400

    # El QR ya usado se reporta como 'usado'.
    ver = client.post("/api/v1/pharmacy/verify-qr", headers=pharmacist_headers, json={"codigo": codigo})
    assert ver.json()["estado_qr"] == "usado"


def test_rechazo_de_receta(client, doctor_headers, auth_headers, pharmacist_headers, monkeypatch):
    rid = _validated_recipe(client, doctor_headers, auth_headers, monkeypatch)
    client.post(f"/api/v1/prescriptions/{rid}/generate-qr", headers=doctor_headers)

    # Rechazo exige observación.
    sin_obs = client.post(f"/api/v1/pharmacy/recipes/{rid}/reject", headers=pharmacist_headers, json={"observaciones": ""})
    assert sin_obs.status_code == 422

    rej = client.post(f"/api/v1/pharmacy/recipes/{rid}/reject", headers=pharmacist_headers, json={"observaciones": "Stock insuficiente"})
    assert rej.status_code == 200 and rej.json()["estado"] == "rechazada"

    # El QR rechazado se reporta como 'anulado'.
    codigo = rej.json()["codigo_verificacion"]
    assert client.post("/api/v1/pharmacy/verify-qr", headers=pharmacist_headers, json={"codigo": codigo}).json()["estado_qr"] == "anulado"


# --- Permisos -------------------------------------------------------------------

def test_permisos_farmacia(client, doctor_headers, auth_headers, pharmacist_headers, monkeypatch):
    rid = _validated_recipe(client, doctor_headers, auth_headers, monkeypatch)
    codigo = client.post(f"/api/v1/prescriptions/{rid}/generate-qr", headers=doctor_headers).json()["codigo_verificacion"]

    # Generar QR: solo médico (farmacéutico no).
    assert client.post(f"/api/v1/prescriptions/{rid}/generate-qr", headers=pharmacist_headers).status_code == 403

    # Consultar farmacia: farmacéutico, médico y admin.
    assert client.get("/api/v1/pharmacy/recipes", headers=pharmacist_headers).status_code == 200
    assert client.get("/api/v1/pharmacy/recipes", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/pharmacy/recipes", headers=doctor_headers).status_code == 200

    # Dispensar/rechazar: solo farmacéutico (médico y admin no).
    assert client.post(f"/api/v1/pharmacy/recipes/{rid}/dispense", headers=doctor_headers, json={"codigo_verificacion": codigo}).status_code == 403
    assert client.post(f"/api/v1/pharmacy/recipes/{rid}/reject", headers=auth_headers, json={"observaciones": "no"}).status_code == 403
