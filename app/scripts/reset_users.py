"""Reinicia los usuarios del sistema.

Elimina TODOS los usuarios (y los datos que dependen de ellos en este entorno de
demostración) y crea un usuario por rol, todos con la contraseña ``123456``.

Uso:
    python -m app.scripts.reset_users
"""

from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User

# (username, nombre, apellido, correo, rol)
DEMO_USERS = [
    ("admin", "Administrador", "Principal", "admin@pharmagnostic.com", "admin"),
    ("doctor", "Doctor", "Demo", "doctor@pharmagnostic.com", "doctor"),
    ("pharmacist", "Farmacéutico", "Demo", "pharmacist@pharmagnostic.com", "pharmacist"),
    ("patient", "Paciente", "Demo", "patient@pharmagnostic.com", "patient"),
]

DEFAULT_PASSWORD = "123456"


def reset_users() -> None:
    db = SessionLocal()
    try:
        # En este entorno los usuarios están referenciados por bitácoras, recetas, etc.
        # TRUNCATE ... CASCADE limpia esas dependencias (datos de prueba) y reinicia los IDs.
        db.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        db.commit()

        roles = {role.nombre: role.id_rol for role in db.query(Role).all()}
        password_hash = hash_password(DEFAULT_PASSWORD)

        for username, nombre, apellido, correo, rol in DEMO_USERS:
            if rol not in roles:
                print(f"  ! Rol '{rol}' no existe; omitiendo {username}. Ejecute el seed de roles.")
                continue
            db.add(
                User(
                    username=username,
                    nombre=nombre,
                    apellido=apellido,
                    correo=correo,
                    contrasena_hash=password_hash,
                    id_rol=roles[rol],
                    activo=True,
                )
            )
        db.commit()
        print("Usuarios reiniciados. Credenciales (contraseña 123456):")
        for username, _, _, _, rol in DEMO_USERS:
            print(f"  - {username} / 123456  ({rol})")
    finally:
        db.close()


if __name__ == "__main__":
    reset_users()
