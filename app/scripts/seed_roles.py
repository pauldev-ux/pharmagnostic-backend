from app.core.database import SessionLocal
from app.models.role import Role

ROLE_NAMES = [
    ("admin", "Administrador del sistema."),
    ("doctor", "Médico que registra pacientes, diagnósticos y recetas."),
    ("pharmacist", "Farmacéutico que gestiona medicamentos y dispensa recetas."),
    ("patient", "Paciente del sistema."),
]


def seed_roles() -> None:
    db = SessionLocal()
    try:
        created = 0
        for nombre, descripcion in ROLE_NAMES:
            existing = db.query(Role).filter(Role.nombre == nombre).first()
            if existing:
                # Mantener idempotencia: actualiza la descripción si cambió.
                if existing.descripcion != descripcion:
                    existing.descripcion = descripcion
            else:
                db.add(Role(nombre=nombre, descripcion=descripcion))
                created += 1
        db.commit()
        print(f"Roles iniciales verificados. Nuevos roles creados: {created}.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()
