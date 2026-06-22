import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class HealthRepository:
    def __init__(self, db: Session):
        self.db = db

    def check_database_connection(self) -> bool:
        try:
            self.db.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.error("Health check: no se pudo validar PostgreSQL: %s", exc)
            return False
