from typing import Optional

from sqlalchemy.orm import Session

from app.models.validacion_ia import ValidacionIA


class ValidacionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, validacion_id: int) -> Optional[ValidacionIA]:
        return (
            self.db.query(ValidacionIA)
            .filter(ValidacionIA.id_validacion == validacion_id)
            .first()
        )

    def get_by_recipe(self, recipe_id: int) -> list[ValidacionIA]:
        return (
            self.db.query(ValidacionIA)
            .filter(ValidacionIA.id_receta == recipe_id)
            .order_by(ValidacionIA.id_validacion.desc())
            .all()
        )

    def add(self, validacion: ValidacionIA) -> None:
        self.db.add(validacion)
