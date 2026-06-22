from tests.conftest import requires_db


def test_login_requires_valid_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "noexiste", "contrasena": "loquesea1A"},
    )
    assert response.status_code == 401


def test_protected_route_without_token(client):
    response = client.get("/api/v1/users")
    assert response.status_code in {401, 403}


@requires_db
def test_login_and_me(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["rol"] == "admin"
    # No debe exponerse el hash de la contraseña.
    assert "contrasena_hash" not in body


@requires_db
def test_users_list_does_not_leak_password(client, auth_headers):
    response = client.get("/api/v1/users", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "items" in body and "total" in body
    for user in body["items"]:
        assert "contrasena_hash" not in user
        assert "password_hash" not in user


@requires_db
def test_refresh_token_flow(client):
    from app.core.config import get_settings

    settings = get_settings()
    login = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.INITIAL_ADMIN_USERNAME,
            "contrasena": settings.INITIAL_ADMIN_PASSWORD,
        },
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert "access_token" in refreshed.json()


@requires_db
def test_prescription_created_with_multiple_items(client, auth_headers, doctor_headers):
    import random

    # Paciente (lo registra el médico, con el modelo del Bloque 2)
    patient = client.post(
        "/api/v1/patients",
        headers=doctor_headers,
        json={
            "nombre": "Paciente",
            "apellido": "Prueba",
            "ci": f"CI{random.randint(10_000_000, 99_999_999)}",
            "fecha_nacimiento": "1990-01-01",
        },
    )
    assert patient.status_code == 201, patient.text
    patient_id = patient.json()["id_paciente"]

    # Dos medicamentos
    med1 = client.post(
        "/api/v1/medications",
        headers=auth_headers,
        json={"nombre": "Paracetamol 500", "presentacion": "Tableta"},
    )
    med2 = client.post(
        "/api/v1/medications",
        headers=auth_headers,
        json={"nombre": "Ibuprofeno 400", "presentacion": "Tableta"},
    )
    assert med1.status_code == 201 and med2.status_code == 201
    med1_id = med1.json()["id_medicamento"]
    med2_id = med2.json()["id_medicamento"]

    # Receta con dos ítems en una sola transacción
    prescription = client.post(
        "/api/v1/prescriptions",
        headers=auth_headers,
        json={
            "id_paciente": patient_id,
            "notas": "Tratamiento de prueba",
            "items": [
                {"id_medicamento": med1_id, "cantidad": 1, "dosis": "1 cada 8h"},
                {"id_medicamento": med2_id, "cantidad": 2, "dosis": "1 cada 12h"},
            ],
        },
    )
    assert prescription.status_code == 201, prescription.text
    body = prescription.json()
    assert len(body["items"]) == 2
    assert body["estado"] == "active"

    # Cancelar (no se elimina físicamente)
    cancelled = client.patch(
        f"/api/v1/prescriptions/{body['id_receta']}/status",
        headers=auth_headers,
        json={"estado": "cancelled"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["estado"] == "cancelled"


@requires_db
def test_prescription_rejects_unknown_medication(client, auth_headers, doctor_headers):
    import random

    patient = client.post(
        "/api/v1/patients",
        headers=doctor_headers,
        json={
            "nombre": "Paciente",
            "apellido": "SinMed",
            "ci": f"CI{random.randint(10_000_000, 99_999_999)}",
            "fecha_nacimiento": "1990-01-01",
        },
    )
    patient_id = patient.json()["id_paciente"]
    response = client.post(
        "/api/v1/prescriptions",
        headers=auth_headers,
        json={"id_paciente": patient_id, "items": [{"id_medicamento": 999999}]},
    )
    assert response.status_code == 404
