"""Seed idempotente: crea los roles base y el administrador inicial.

Uso:
    python -m app.scripts.seed
"""

from app.scripts.create_initial_admin import create_initial_admin
from app.scripts.seed_roles import seed_roles


def run() -> None:
    seed_roles()
    create_initial_admin()


if __name__ == "__main__":
    run()
