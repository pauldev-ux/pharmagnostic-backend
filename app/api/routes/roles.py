from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_admin
from app.repositories.role_repository import RoleRepository
from app.schemas.role import RoleOut
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleOut])
def list_roles(
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    service = RoleService(RoleRepository(db))
    return service.get_all_roles()
