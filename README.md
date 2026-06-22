# Pharmagnostic Backend

## Descripción
Backend del proyecto PHARMAGNOSTIC AI, construido con FastAPI, PostgreSQL, SQLAlchemy, Psycopg y Alembic.
Incluye autenticación JWT (login, usuario actual, refresh, logout), permisos por rol y CRUD con
búsqueda, filtros y paginación para usuarios, pacientes, diagnósticos, medicamentos y recetas.

## Requisitos
- Python 3.11+
- PostgreSQL (base `pharmagnostic_ai`)

## Variables de entorno
Copia `.env.example` a `.env` y ajusta los valores. La cadena de conexión vive **solo** en `.env`
(ignorado por git). Por defecto:
`postgresql+psycopg://postgres:123456@localhost:5432/pharmagnostic_ai`

## Puesta en marcha (sin Docker)
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate        # Linux/macOS
pip install -r requirements.txt

# 1) Migraciones (crea todas las tablas)
alembic upgrade head

# 2) Seed idempotente (roles admin/doctor/pharmacist/patient + administrador inicial)
python -m app.scripts.seed

# 3) (Opcional) Reiniciar usuarios de demostración (1 por rol, contraseña 123456)
python -m app.scripts.reset_users

# 4) Levantar el backend
uvicorn app.main:app --reload
```

El **login es por `username`** (no por correo). Usuarios de demostración (contraseña `123456`):

| Usuario | Rol |
|---------|-----|
| `admin` | admin |
| `doctor` | doctor |
| `pharmacist` | pharmacist |
| `patient` | patient |

## Pruebas
```bash
pytest
```

## Rutas principales
- `GET /docs` — Swagger UI
- `GET /api/health` y `GET /api/v1/health` — estado del servicio (verifica PostgreSQL con `SELECT 1`)
- `POST /api/v1/auth/login`, `/auth/refresh`, `/auth/logout`, `GET /auth/me`
- `/api/v1/users`, `/patients`, `/diagnoses`, `/medications`, `/prescriptions`, `/profile`, `/roles`
