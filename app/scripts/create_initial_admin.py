from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User

settings = get_settings()


def create_initial_admin() -> None:
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.nombre == "admin").first()
        if not role:
            print("No existe el rol admin. Ejecute primero el seed de roles.")
            return

        email = settings.INITIAL_ADMIN_EMAIL.lower()
        user = db.query(User).filter(User.correo == email).first()
        if user:
            print(f"El administrador inicial ya existe: {email}")
            return

        admin = User(
            username=settings.INITIAL_ADMIN_USERNAME,
            nombre=settings.INITIAL_ADMIN_NAME,
            apellido=settings.INITIAL_ADMIN_LAST_NAME,
            correo=email,
            contrasena_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
            id_rol=role.id_rol,
            activo=True,
        )
        db.add(admin)
        db.commit()
        print(f"Administrador creado correctamente: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    create_initial_admin()
