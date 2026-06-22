from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    correo: EmailStr
    contrasena: str = Field(min_length=6)
    id_rol: int
    numero_licencia: Optional[str] = None
    activo: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(default=None, min_length=1, max_length=100)
    correo: Optional[EmailStr] = None
    id_rol: Optional[int] = None
    numero_licencia: Optional[str] = None


class UserStatusUpdate(BaseModel):
    activo: bool


class UserPasswordUpdate(BaseModel):
    nueva_contrasena: str = Field(min_length=6)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    id_rol: int
    username: str
    nombre: str
    apellido: str
    correo: str
    numero_licencia: Optional[str] = None
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: Optional[datetime] = None
