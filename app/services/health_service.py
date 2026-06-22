from app.repositories.health_repository import HealthRepository


class HealthService:
    def __init__(self, repository: HealthRepository):
        self.repository = repository

    def get_health_status(self) -> dict:
        database_connected = self.repository.check_database_connection()
        return {
            "service": "pharmagnostic-backend",
            "backend": "ok",
            "database": "connected" if database_connected else "disconnected",
            "status": (
                "API disponible"
                if database_connected
                else "API disponible con problemas de base de datos"
            ),
        }
