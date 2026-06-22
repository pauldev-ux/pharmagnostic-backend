from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(default=None, min_length=1, max_length=100)
    correo: Optional[EmailStr] = None
    numero_licencia: Optional[str] = Field(default=None, max_length=50)


class PasswordChange(BaseModel):
    contrasena_actual: str = Field(min_length=1)
    nueva_contrasena: str = Field(min_length=8)
