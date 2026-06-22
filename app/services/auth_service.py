from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services import auditoria_service


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)

    @staticmethod
    def _public_user(user: User) -> dict:
        return {
            "id_usuario": user.id_usuario,
            "username": user.username,
            "nombre": user.nombre,
            "apellido": user.apellido,
            "correo": user.correo,
            "rol": user.rol.nombre,
            "activo": user.activo,
        }

    def _build_tokens(self, user: User) -> dict:
        token_payload = create_access_token(user.id_usuario, user.rol.nombre)
        refresh_token = create_refresh_token(user.id_usuario, user.rol.nombre)
        return {
            **token_payload,
            "refresh_token": refresh_token,
            "usuario": self._public_user(user),
        }

    def login(self, username: str, contrasena: str) -> dict:
        user = self.repository.get_by_username(username.strip().lower())
        if not user or not verify_password(contrasena, user.contrasena_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contraseña incorrectos",
            )
        if not user.activo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario inactivo",
            )
        auditoria_service.registrar(
            self.db, accion="login", modulo="auth", tabla_afectada="users",
            id_registro=user.id_usuario, detalle=f"Inicio de sesión de '{user.username}'",
            user_id=user.id_usuario, commit=True,
        )
        return self._build_tokens(user)

    def refresh(self, refresh_token: str) -> dict:
        try:
            payload = decode_refresh_token(refresh_token)
            user_id = int(payload["sub"])
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de actualización inválido",
            )

        user = self.repository.get_by_id(user_id)
        if not user or not user.activo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de actualización inválido",
            )
        return self._build_tokens(user)
