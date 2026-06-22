import random
from datetime import timedelta

from app.core.security import _create_token
from tests.conftest import requires_db

pytestmark = requires_db


def test_jwt_expirado_rechazado(client):
    # Token de acceso ya expirado.
    expirado = _create_token(1, "admin", "access", timedelta(seconds=-10))
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expirado}"})
    assert res.status_code == 401


def test_jwt_invalido_rechazado(client):
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer no-es-un-token"})
    assert res.status_code == 401


def test_login_credenciales_incorrectas(client):
    res = client.post("/api/v1/auth/login", json={"username": "admin", "contrasena": "mala"})
    assert res.status_code == 401


def test_usuario_inactivo_no_inicia_sesion(client, auth_headers):
    uname = f"inact{random.randint(1, 999999)}"
    rol_id = next(
        r["id_rol"] for r in client.get("/api/v1/roles", headers=auth_headers).json() if r["nombre"] == "doctor"
    )
    uid = client.post(
        "/api/v1/users", headers=auth_headers,
        json={"username": uname, "nombre": "In", "apellido": "Activo", "correo": f"{uname}@x.com",
              "contrasena": "123456", "id_rol": rol_id},
    ).json()["id_usuario"]
    # Iniciar sesión activo funciona.
    assert client.post("/api/v1/auth/login", json={"username": uname, "contrasena": "123456"}).status_code == 200
    # Desactivar.
    client.patch(f"/api/v1/users/{uid}/status", headers=auth_headers, json={"activo": False})
    # Ya no puede iniciar sesión.
    assert client.post("/api/v1/auth/login", json={"username": uname, "contrasena": "123456"}).status_code == 401


def test_token_de_usuario_desactivado_rechazado(client, auth_headers):
    uname = f"des{random.randint(1, 999999)}"
    rol_id = next(
        r["id_rol"] for r in client.get("/api/v1/roles", headers=auth_headers).json() if r["nombre"] == "doctor"
    )
    uid = client.post(
        "/api/v1/users", headers=auth_headers,
        json={"username": uname, "nombre": "Des", "apellido": "Activado", "correo": f"{uname}@x.com",
              "contrasena": "123456", "id_rol": rol_id},
    ).json()["id_usuario"]
    token = client.post("/api/v1/auth/login", json={"username": uname, "contrasena": "123456"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    # Desactivar al usuario invalida su token en uso.
    client.patch(f"/api/v1/users/{uid}/status", headers=auth_headers, json={"activo": False})
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_sin_token_rechazado(client):
    assert client.get("/api/v1/users").status_code in {401, 403}
