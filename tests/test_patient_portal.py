import random

from app.services import ollama_client
from app.schemas.patient_portal import REFUSAL
from tests.conftest import requires_db

pytestmark = requires_db


def _ci() -> str:
    return f"CI{random.randint(10_000_000, 99_999_999)}"


def _patient_user_id() -> int:
    """ID del usuario demo con rol paciente (username 'paciente')."""
    from app.core.database import SessionLocal
    from app.models.role import Role
    from app.models.user import User

    db = SessionLocal()
    try:
        u = db.query(User).join(Role, User.id_rol == Role.id_rol).filter(Role.nombre == "patient").first()
        assert u is not None
        return u.id_usuario
    finally:
        db.close()


def _patient_headers(client) -> dict:
    r = client.post("/api/v1/auth/login", json={"username": "paciente", "contrasena": "123456"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_linked_patient(client, doctor_headers, user_id: int, ci=None) -> int:
    res = client.post(
        "/api/v1/patients",
        headers=doctor_headers,
        json={"nombre": "Portal", "apellido": "Paciente", "ci": ci or _ci(),
              "fecha_nacimiento": "1990-05-05", "id_usuario": user_id},
    )
    assert res.status_code == 201, res.text
    return res.json()["id_paciente"]


def _create_recipe(client, doctor_headers, auth_headers, patient_id: int) -> int:
    med = client.post("/api/v1/medications", headers=auth_headers, json={"nombre": f"Med {random.randint(1,9999)}"}).json()["id_medicamento"]
    r = client.post(
        "/api/v1/prescriptions", headers=doctor_headers,
        json={"id_paciente": patient_id, "items": [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h", "instrucciones": "oral 3 días"}]},
    )
    return r.json()["id_receta"]


def _ensure_linked_patient(client, doctor_headers):
    """Crea (si no existe) un paciente vinculado a la cuenta demo 'paciente'."""
    uid = _patient_user_id()
    from app.core.database import SessionLocal
    from app.models.patient import Patient

    db = SessionLocal()
    try:
        existing = db.query(Patient).filter(Patient.id_usuario == uid).first()
        if existing:
            return existing.id_paciente
    finally:
        db.close()
    return _create_linked_patient(client, doctor_headers, uid)


# --- Perfil y recetas -----------------------------------------------------------

def test_consulta_perfil(client, doctor_headers):
    _ensure_linked_patient(client, doctor_headers)
    headers = _patient_headers(client)
    res = client.get("/api/v1/patient-portal/profile", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["nombre"] and "edad" in body
    # No expone datos técnicos/clínicos sensibles.
    assert "alergias" not in body and "antecedentes_medicos" not in body and "observaciones" not in body


def test_listado_recetas_propias(client, doctor_headers, auth_headers):
    pid = _ensure_linked_patient(client, doctor_headers)
    _create_recipe(client, doctor_headers, auth_headers, pid)
    headers = _patient_headers(client)
    res = client.get("/api/v1/patient-portal/recipes", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert len(body) >= 1
    assert body[0]["estado"] in {"borrador", "validada", "bloqueada", "dispensada", "anulada"}
    # No expone notas internas ni datos de IA.
    assert "notas" not in body[0] and "resumen" not in body[0]


def test_no_consultar_receta_ajena(client, doctor_headers, auth_headers):
    _ensure_linked_patient(client, doctor_headers)
    headers = _patient_headers(client)
    # Receta de OTRO paciente (no vinculado a la cuenta).
    otro_pid = client.post(
        "/api/v1/patients", headers=doctor_headers,
        json={"nombre": "Otro", "apellido": "Paciente", "ci": _ci(), "fecha_nacimiento": "1980-01-01"},
    ).json()["id_paciente"]
    ajena = _create_recipe(client, doctor_headers, auth_headers, otro_pid)
    res = client.get(f"/api/v1/patient-portal/recipes/{ajena}", headers=headers)
    assert res.status_code == 404  # no se filtra existencia


def test_paciente_sin_recetas(client, doctor_headers, auth_headers):
    # Cuenta de paciente nueva y vinculada, sin recetas -> listado vacío.
    rol_id = next(r["id_rol"] for r in client.get("/api/v1/roles", headers=auth_headers).json() if r["nombre"] == "patient")
    uname = f"pac{random.randint(1, 99999)}"
    uid = client.post(
        "/api/v1/users", headers=auth_headers,
        json={"username": uname, "nombre": "Sin", "apellido": "Recetas", "correo": f"{uname}@x.com", "contrasena": "123456", "id_rol": rol_id},
    ).json()["id_usuario"]
    _create_linked_patient(client, doctor_headers, uid)
    tok = client.post("/api/v1/auth/login", json={"username": uname, "contrasena": "123456"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}
    res = client.get("/api/v1/patient-portal/recipes", headers=headers)
    assert res.status_code == 200 and res.json() == []


# --- Chatbot --------------------------------------------------------------------

def test_chat_pregunta_permitida(client, doctor_headers, monkeypatch):
    _ensure_linked_patient(client, doctor_headers)
    monkeypatch.setattr(ollama_client, "chat", lambda system, prompt: "El estado de tu receta es validada.")
    headers = _patient_headers(client)
    res = client.post("/api/v1/patient-portal/chat", headers=headers, json={"mensaje": "¿Cuál es el estado de mi receta?"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert "no sustituye" in body["disclaimer"]
    assert body["respuesta"]


def test_chat_diagnostico_rechazado(client, doctor_headers):
    _ensure_linked_patient(client, doctor_headers)
    headers = _patient_headers(client)
    res = client.post(
        "/api/v1/patient-portal/chat", headers=headers,
        json={"mensaje": "Diagnostícame, ¿qué enfermedad tengo según mis síntomas?"},
    )
    assert res.status_code == 200
    assert res.json()["respuesta"] == REFUSAL


def test_chat_limita_longitud(client, doctor_headers):
    _ensure_linked_patient(client, doctor_headers)
    headers = _patient_headers(client)
    res = client.post("/api/v1/patient-portal/chat", headers=headers, json={"mensaje": "a" * 501})
    assert res.status_code == 422


# --- Permisos -------------------------------------------------------------------

def test_permisos_otros_roles(client, doctor_headers, auth_headers, pharmacist_headers):
    # Médico, admin y farmacéutico NO acceden al portal del paciente.
    for h in (doctor_headers, auth_headers, pharmacist_headers):
        assert client.get("/api/v1/patient-portal/profile", headers=h).status_code == 403
        assert client.get("/api/v1/patient-portal/recipes", headers=h).status_code == 403
    assert client.get("/api/v1/patient-portal/profile").status_code in {401, 403}
