from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=50)
    descripcion: Optional[str] = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_rol: int
    nombre: str
    descripcion: Optional[str] = None
