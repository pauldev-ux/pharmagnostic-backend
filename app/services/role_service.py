from typing import Optional

from app.models.role import Role
from app.repositories.role_repository import RoleRepository


class RoleService:
    def __init__(self, repository: RoleRepository):
        self.repository = repository

    def get_all_roles(self) -> list[Role]:
        return self.repository.get_all()

    def get_role_by_id(self, role_id: int) -> Optional[Role]:
        return self.repository.get_by_id(role_id)
