from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.correo == email).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id_usuario == user_id).first()

    def get_all(
        self,
        search: Optional[str] = None,
        role_id: Optional[int] = None,
        active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        query = self.db.query(User)

        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(term),
                    User.nombre.ilike(term),
                    User.apellido.ilike(term),
                    User.correo.ilike(term),
                )
            )

        if role_id is not None:
            query = query.filter(User.id_rol == role_id)

        if active is not None:
            query = query.filter(User.activo == active)

        total = query.count()
        users = query.order_by(User.id_usuario).offset(skip).limit(limit).all()
        return users, total

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        user.fecha_actualizacion = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_logic(self, user: User) -> User:
        user.activo = False
        user.fecha_actualizacion = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user
