import random

from sqlalchemy import text

from app.core.database import SessionLocal
from app.scripts.reset_clinical_data import reset_clinical_data
from tests.conftest import requires_db

pytestmark = requires_db


def _ci() -> str:
    return f"CI{random.randint(10_000_000, 99_999_999)}"


def _create_patient(client, doctor_headers, **overrides) -> dict:
    payload = {
        "nombre": "Hist",
        "apellido": "Clínico",
        "ci": _ci(),
        "fecha_nacimiento": "1988-07-10",
        "sexo": "masculino",
    }
    payload.update(overrides)
    res = client.post("/api/v1/patients", headers=doctor_headers, json=payload)
    assert res.status_code == 201, res.text
    return res.json()


# --- Historial clínico ----------------------------------------------------------

def test_crear_historial_clinico(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    res = client.post(
        f"/api/v1/patients/{pid}/clinical-history",
        headers=doctor_headers,
        json={"tipo_evento": "alergia", "descripcion": "Alergia a penicilina"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["tipo_evento"] == "alergia"
    assert body["activo"] is True


def test_editar_y_desactivar_historial(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    hid = client.post(
        f"/api/v1/patients/{pid}/clinical-history",
        headers=doctor_headers,
        json={"tipo_evento": "observacion", "descripcion": "Inicial"},
    ).json()["id_historial"]

    upd = client.patch(
        f"/api/v1/clinical-history/{hid}",
        headers=doctor_headers,
        json={"tipo_evento": "cirugia", "descripcion": "Apendicectomía 2019"},
    )
    assert upd.status_code == 200
    assert upd.json()["tipo_evento"] == "cirugia"
    assert upd.json()["descripcion"] == "Apendicectomía 2019"

    baja = client.patch(
        f"/api/v1/clinical-history/{hid}/status", headers=doctor_headers, json={"activo": False}
    )
    assert baja.status_code == 200 and baja.json()["activo"] is False


def test_historial_tipo_invalido(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    res = client.post(
        f"/api/v1/patients/{pid}/clinical-history",
        headers=doctor_headers,
        json={"tipo_evento": "consulta_no_valida", "descripcion": "x"},
    )
    assert res.status_code == 422


def test_historial_solo_medico(client, doctor_headers, auth_headers, pharmacist_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    payload = {"tipo_evento": "otro", "descripcion": "intento"}
    # El admin es superusuario: puede gestionar historial.
    assert client.post(f"/api/v1/patients/{pid}/clinical-history", headers=auth_headers, json=payload).status_code == 201
    # El farmacéutico no.
    assert (
        client.post(f"/api/v1/patients/{pid}/clinical-history", headers=pharmacist_headers, json=payload).status_code
        == 403
    )


def test_historial_paciente_inactivo(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    client.patch(f"/api/v1/patients/{pid}/status", headers=doctor_headers, json={"activo": False})
    res = client.post(
        f"/api/v1/patients/{pid}/clinical-history",
        headers=doctor_headers,
        json={"tipo_evento": "otro", "descripcion": "no permitido"},
    )
    assert res.status_code == 400


# --- Diagnósticos ---------------------------------------------------------------

def test_crear_diagnostico_con_fecha_registro(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    res = client.post(
        f"/api/v1/patients/{pid}/diagnoses",
        headers=doctor_headers,
        json={"descripcion": "Hipertensión", "tipo": "confirmado", "codigo_cie10": "i10"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["codigo_cie10"] == "I10"  # normalizado a mayúsculas
    assert body["fecha_registro"] is not None
    assert body["tipo"] == "confirmado"


def test_diagnostico_cie10_opcional(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    res = client.post(
        f"/api/v1/patients/{pid}/diagnoses",
        headers=doctor_headers,
        json={"descripcion": "Sin código CIE-10"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["codigo_cie10"] is None


def test_diagnostico_tipo_invalido(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    res = client.post(
        f"/api/v1/patients/{pid}/diagnoses",
        headers=doctor_headers,
        json={"descripcion": "x", "tipo": "sospecha"},
    )
    assert res.status_code == 422


def test_diagnostico_solo_medico(client, doctor_headers, auth_headers, pharmacist_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    payload = {"descripcion": "intento"}
    # El admin (superusuario) puede crear; el farmacéutico no.
    assert client.post(f"/api/v1/patients/{pid}/diagnoses", headers=auth_headers, json=payload).status_code == 201
    assert (
        client.post(f"/api/v1/patients/{pid}/diagnoses", headers=pharmacist_headers, json=payload).status_code == 403
    )
    # El administrador también puede consultar.
    assert client.get(f"/api/v1/patients/{pid}/diagnoses", headers=auth_headers).status_code == 200


def test_diagnostico_paciente_inactivo(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    client.patch(f"/api/v1/patients/{pid}/status", headers=doctor_headers, json={"activo": False})
    res = client.post(
        f"/api/v1/patients/{pid}/diagnoses",
        headers=doctor_headers,
        json={"descripcion": "no permitido"},
    )
    assert res.status_code == 400


# --- Limpieza segura (development) ----------------------------------------------

def test_limpieza_segura_en_development(client, doctor_headers):
    # Generar datos para asegurar conteos > 0.
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    client.post(
        f"/api/v1/patients/{pid}/clinical-history",
        headers=doctor_headers,
        json={"tipo_evento": "antecedente", "descripcion": "dato"},
    )
    client.post(
        f"/api/v1/patients/{pid}/diagnoses", headers=doctor_headers, json={"descripcion": "dato"}
    )

    db = SessionLocal()
    try:
        users_before = db.execute(text("SELECT count(*) FROM users")).scalar_one()
        roles_before = db.execute(text("SELECT count(*) FROM roles")).scalar_one()
        assert db.execute(text("SELECT count(*) FROM patients")).scalar_one() > 0

        reset_clinical_data(confirm=True)

        for table in ("patients", "medications", "prescriptions", "prescription_items", "diagnoses", "clinical_history"):
            assert db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0, table

        # Usuarios y roles intactos.
        assert db.execute(text("SELECT count(*) FROM users")).scalar_one() == users_before
        assert db.execute(text("SELECT count(*) FROM roles")).scalar_one() == roles_before
    finally:
        db.close()
