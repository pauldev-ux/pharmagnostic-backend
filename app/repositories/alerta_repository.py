from typing import Optional

from sqlalchemy.orm import Session

from app.models.alerta_clinica import AlertaClinica


class AlertaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, alerta_id: int) -> Optional[AlertaClinica]:
        return self.db.query(AlertaClinica).filter(AlertaClinica.id_alerta == alerta_id).first()

    def get_by_recipe(self, recipe_id: int) -> list[AlertaClinica]:
        return (
            self.db.query(AlertaClinica)
            .filter(AlertaClinica.id_receta == recipe_id)
            .order_by(AlertaClinica.nivel.desc(), AlertaClinica.id_alerta.desc())
            .all()
        )

    def delete_by_recipe(self, recipe_id: int) -> int:
        """Elimina las alertas preliminares previas de la receta. Devuelve cuántas borró."""
        deleted = (
            self.db.query(AlertaClinica)
            .filter(AlertaClinica.id_receta == recipe_id)
            .delete(synchronize_session=False)
        )
        return deleted

    def add_all(self, alertas: list[AlertaClinica]) -> None:
        self.db.add_all(alertas)

    def save(self, alerta: AlertaClinica) -> AlertaClinica:
        self.db.commit()
        self.db.refresh(alerta)
        return alerta
