import random
from datetime import date, timedelta

from tests.conftest import requires_db

pytestmark = requires_db


def _ci() -> str:
    return f"CI{random.randint(10_000_000, 99_999_999)}"


def _patient_payload(**overrides) -> dict:
    data = {
        "nombre": "Juan",
        "apellido": "Pérez",
        "ci": _ci(),
        "fecha_nacimiento": "1990-05-20",
        "sexo": "masculino",
        "telefono": "70000000",
        "correo": "Juan.Perez@Example.com",
        "funcion_renal": "normal",
        "funcion_hepatica": "leve",
    }
    data.update(overrides)
    return data


def _create_patient(client, doctor_headers, **overrides) -> dict:
    res = client.post("/api/v1/patients", headers=doctor_headers, json=_patient_payload(**overrides))
    assert res.status_code == 201, res.text
    return res.json()


# --- Registro y normalización ---------------------------------------------------

def test_registrar_paciente_normaliza_correo(client, doctor_headers):
    body = _create_patient(client, doctor_headers)
    assert body["id_paciente"] > 0
    assert body["activo"] is True
    assert body["correo"] == "juan.perez@example.com"  # normalizado a minúsculas
    assert "edad" in body


def test_ci_duplicado(client, doctor_headers):
    ci = _ci()
    _create_patient(client, doctor_headers, ci=ci)
    res = client.post("/api/v1/patients", headers=doctor_headers, json=_patient_payload(ci=ci))
    assert res.status_code == 409


def test_fecha_nacimiento_futura(client, doctor_headers):
    futura = (date.today() + timedelta(days=1)).isoformat()
    res = client.post(
        "/api/v1/patients", headers=doctor_headers, json=_patient_payload(fecha_nacimiento=futura)
    )
    assert res.status_code == 422


def test_calculo_edad(client, doctor_headers):
    nacimiento = date.today() - timedelta(days=365 * 25 + 10)
    body = _create_patient(client, doctor_headers, fecha_nacimiento=nacimiento.isoformat())
    hoy = date.today()
    esperada = hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))
    assert body["edad"] == esperada


def test_actualizar_y_baja_logica(client, doctor_headers):
    body = _create_patient(client, doctor_headers)
    pid = body["id_paciente"]

    upd = client.patch(f"/api/v1/patients/{pid}", headers=doctor_headers, json={"telefono": "71111111"})
    assert upd.status_code == 200
    assert upd.json()["telefono"] == "71111111"

    baja = client.patch(f"/api/v1/patients/{pid}/status", headers=doctor_headers, json={"activo": False})
    assert baja.status_code == 200
    assert baja.json()["activo"] is False

    # Baja lógica: el paciente sigue existiendo.
    get = client.get(f"/api/v1/patients/{pid}", headers=doctor_headers)
    assert get.status_code == 200
    assert get.json()["activo"] is False


# --- Permisos por rol -----------------------------------------------------------

def test_permisos_admin_consulta_y_crea(client, doctor_headers, auth_headers):
    _create_patient(client, doctor_headers)
    # Admin puede consultar pacientes.
    assert client.get("/api/v1/patients", headers=auth_headers).status_code == 200
    # Admin también puede registrar pacientes (admin + médico).
    assert client.post("/api/v1/patients", headers=auth_headers, json=_patient_payload()).status_code == 201


def test_permisos_farmaceutico_sin_acceso(client, pharmacist_headers):
    assert client.get("/api/v1/patients", headers=pharmacist_headers).status_code == 403
    assert client.post("/api/v1/patients", headers=pharmacist_headers, json=_patient_payload()).status_code == 403


def test_sin_token_no_autorizado(client):
    assert client.get("/api/v1/patients").status_code in {401, 403}


# --- Historial clínico ----------------------------------------------------------

def test_historial_clinico_crud(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]

    crear = client.post(
        f"/api/v1/patients/{pid}/clinical-history",
        headers=doctor_headers,
        json={"tipo_evento": "observacion", "descripcion": "Control general"},
    )
    assert crear.status_code == 201, crear.text
    hid = crear.json()["id_historial"]

    listado = client.get(f"/api/v1/patients/{pid}/clinical-history", headers=doctor_headers)
    assert listado.status_code == 200
    assert listado.json()["total"] >= 1

    upd = client.patch(
        f"/api/v1/clinical-history/{hid}", headers=doctor_headers, json={"descripcion": "Editado"}
    )
    assert upd.status_code == 200
    assert upd.json()["descripcion"] == "Editado"

    baja = client.patch(
        f"/api/v1/clinical-history/{hid}/status", headers=doctor_headers, json={"activo": False}
    )
    assert baja.status_code == 200
    assert baja.json()["activo"] is False


# --- Diagnósticos ---------------------------------------------------------------

def test_diagnostico_crud_y_normaliza_cie10(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]

    crear = client.post(
        f"/api/v1/patients/{pid}/diagnoses",
        headers=doctor_headers,
        json={"codigo_cie10": "j06.9", "descripcion": "Infección respiratoria", "tipo": "preliminar"},
    )
    assert crear.status_code == 201, crear.text
    did = crear.json()["id_diagnostico"]
    assert crear.json()["codigo_cie10"] == "J06.9"  # normalizado a mayúsculas

    assert client.get(f"/api/v1/diagnoses/{did}", headers=doctor_headers).status_code == 200

    listado = client.get(f"/api/v1/patients/{pid}/diagnoses", headers=doctor_headers)
    assert listado.status_code == 200 and listado.json()["total"] >= 1

    upd = client.patch(
        f"/api/v1/diagnoses/{did}", headers=doctor_headers, json={"tipo": "confirmado"}
    )
    assert upd.status_code == 200 and upd.json()["tipo"] == "confirmado"

    baja = client.patch(f"/api/v1/diagnoses/{did}/status", headers=doctor_headers, json={"activo": False})
    assert baja.status_code == 200 and baja.json()["activo"] is False


def test_no_diagnostico_en_paciente_inactivo(client, doctor_headers):
    pid = _create_patient(client, doctor_headers)["id_paciente"]
    client.patch(f"/api/v1/patients/{pid}/status", headers=doctor_headers, json={"activo": False})

    diag = client.post(
        f"/api/v1/patients/{pid}/diagnoses",
        headers=doctor_headers,
        json={"descripcion": "No debería permitirse"},
    )
    assert diag.status_code == 400

    evento = client.post(
        f"/api/v1/patients/{pid}/clinical-history",
        headers=doctor_headers,
        json={"tipo_evento": "observacion", "descripcion": "No debería permitirse"},
    )
    assert evento.status_code == 400


def test_no_se_filtran_datos_sensibles(client, doctor_headers):
    _create_patient(client, doctor_headers)
    text = client.get("/api/v1/patients", headers=doctor_headers).text
    assert "contrasena_hash" not in text and "password_hash" not in text
