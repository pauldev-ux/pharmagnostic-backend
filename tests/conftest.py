import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app

settings = get_settings()


def _database_available() -> bool:
    try:
        from sqlalchemy import text

        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception:
        return False


DB_AVAILABLE = _database_available()
requires_db = pytest.mark.skipif(not DB_AVAILABLE, reason="PostgreSQL no disponible")


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_token(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": settings.INITIAL_ADMIN_USERNAME,
            "contrasena": settings.INITIAL_ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


def _username_for_role(role_name: str) -> str:
    """Obtiene el username de un usuario activo con el rol indicado.

    Hace la búsqueda real en la BD para no depender del idioma del username
    (p. ej. 'pharmacist' vs 'farmaceutico').
    """
    from app.models.role import Role
    from app.models.user import User

    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .join(Role, User.id_rol == Role.id_rol)
            .filter(Role.nombre == role_name, User.activo.is_(True))
            .first()
        )
        assert user is not None, f"No existe un usuario con rol '{role_name}'"
        return user.username
    finally:
        db.close()


def _login(client: TestClient, username: str, password: str = "123456") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "contrasena": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def doctor_token(client: TestClient) -> str:
    return _login(client, _username_for_role("doctor"))


@pytest.fixture(scope="session")
def pharmacist_token(client: TestClient) -> str:
    return _login(client, _username_for_role("pharmacist"))


@pytest.fixture()
def doctor_headers(doctor_token: str) -> dict:
    return {"Authorization": f"Bearer {doctor_token}"}


@pytest.fixture()
def pharmacist_headers(pharmacist_token: str) -> dict:
    return {"Authorization": f"Bearer {pharmacist_token}"}
