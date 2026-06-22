from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password, validate_password_strength, verify_password
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)
        self.role_repository = RoleRepository(db)

    def create_user(self, data: dict) -> User:
        email = data["correo"].lower()
        username = data["username"].strip().lower()
        if self.user_repository.get_by_username(username):
            raise HTTPException(status_code=409, detail="El nombre de usuario ya está registrado")
        if self.user_repository.get_by_email(email):
            raise HTTPException(status_code=409, detail="El correo ya está registrado")

        role = self.role_repository.get_by_id(data["id_rol"])
        if not role:
            raise HTTPException(status_code=404, detail="Rol no encontrado")

        if not validate_password_strength(data["contrasena"]):
            raise HTTPException(
                status_code=400,
                detail="La contraseña debe tener al menos 6 caracteres",
            )

        user = User(
            username=username,
            nombre=data["nombre"],
            apellido=data["apellido"],
            correo=email,
            contrasena_hash=hash_password(data["contrasena"]),
            id_rol=data["id_rol"],
            numero_licencia=data.get("numero_licencia"),
            activo=data.get("activo", True),
        )
        return self.user_repository.create(user)

    def get_users(
        self,
        search: str | None = None,
        role_id: int | None = None,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        skip = (page - 1) * page_size
        return self.user_repository.get_all(
            search=search,
            role_id=role_id,
            active=active,
            skip=skip,
            limit=page_size,
        )

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.user_repository.get_by_id(user_id)

    def update_user(self, user_id: int, data: dict) -> User:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        if data.get("username"):
            username = data["username"].strip().lower()
            existing = self.user_repository.get_by_username(username)
            if existing and existing.id_usuario != user_id:
                raise HTTPException(status_code=409, detail="El nombre de usuario ya está registrado")
            user.username = username

        if data.get("correo"):
            email = data["correo"].lower()
            existing = self.user_repository.get_by_email(email)
            if existing and existing.id_usuario != user_id:
                raise HTTPException(status_code=409, detail="El correo ya está registrado")
            user.correo = email

        if data.get("nombre") is not None:
            user.nombre = data["nombre"]
        if data.get("apellido") is not None:
            user.apellido = data["apellido"]
        if data.get("id_rol") is not None:
            role = self.role_repository.get_by_id(data["id_rol"])
            if not role:
                raise HTTPException(status_code=404, detail="Rol no encontrado")
            user.id_rol = data["id_rol"]
        if data.get("numero_licencia") is not None:
            user.numero_licencia = data["numero_licencia"]

        return self.user_repository.update(user)

    def update_status(self, user_id: int, active: bool, current_user: User) -> User:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if user.id_usuario == current_user.id_usuario and not active:
            raise HTTPException(
                status_code=400,
                detail="No puede desactivar su propia cuenta",
            )

        if user.rol.nombre == "admin" and active is False:
            active_admins = (
                self.db.query(User)
                .join(User.rol)
                .filter(User.activo.is_(True), User.id_usuario != user.id_usuario)
                .count()
            )
            if active_admins == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No puede desactivar al último administrador activo",
                )

        user.activo = active
        return self.user_repository.update(user)

    def update_profile(self, user_id: int, data: dict) -> User:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        if data.get("username"):
            username = data["username"].strip().lower()
            existing = self.user_repository.get_by_username(username)
            if existing and existing.id_usuario != user_id:
                raise HTTPException(status_code=409, detail="El nombre de usuario ya está registrado")
            user.username = username

        if data.get("correo"):
            email = data["correo"].lower()
            existing = self.user_repository.get_by_email(email)
            if existing and existing.id_usuario != user_id:
                raise HTTPException(status_code=409, detail="El correo ya está registrado")
            user.correo = email
        if data.get("nombre") is not None:
            user.nombre = data["nombre"]
        if data.get("apellido") is not None:
            user.apellido = data["apellido"]
        if data.get("numero_licencia") is not None:
            user.numero_licencia = data["numero_licencia"]

        return self.user_repository.update(user)

    def change_own_password(
        self, user_id: int, contrasena_actual: str, nueva_contrasena: str
    ) -> User:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if not verify_password(contrasena_actual, user.contrasena_hash):
            raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
        if not validate_password_strength(nueva_contrasena):
            raise HTTPException(
                status_code=400,
                detail="La contraseña debe tener al menos 6 caracteres",
            )
        user.contrasena_hash = hash_password(nueva_contrasena)
        return self.user_repository.update(user)

    def reset_password(self, user_id: int, nueva_contrasena: str) -> User:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if not validate_password_strength(nueva_contrasena):
            raise HTTPException(
                status_code=400,
                detail="La contraseña debe tener al menos 6 caracteres",
            )
        user.contrasena_hash = hash_password(nueva_contrasena)
        return self.user_repository.update(user)
