"""Limpieza manual de los datos clínicos de desarrollo.

Elimina pacientes, medicamentos, recetas (y sus detalles), diagnósticos e
historial clínico. **No** toca usuarios, roles, configuración ni migraciones.

Salvaguardas:
  * Solo se ejecuta si APP_ENV == "development".
  * Muestra los conteos actuales antes de borrar.
  * Borra respetando las llaves foráneas, en una sola transacción.
  * Reinicia las secuencias solo en desarrollo.
  * Requiere confirmación explícita; sin ``--confirm`` solo informa (dry-run).
  * No se ejecuta automáticamente al iniciar la aplicación.

Uso:
    python -m app.scripts.reset_clinical_data            # solo muestra conteos
    python -m app.scripts.reset_clinical_data --confirm  # ejecuta la limpieza
"""

import argparse

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal

settings = get_settings()

# Tablas a limpiar, en orden válido según las llaves foráneas reales del proyecto.
DELETE_ORDER = [
    ("dispensacion", "id_dispensacion"),
    ("validacion_ia", "id_validacion"),
    ("alerta_clinica", "id_alerta"),
    ("audio_clinico", "id_audio"),
    ("prescription_items", "id_item"),
    ("prescriptions", "id_receta"),
    ("diagnoses", "id_diagnostico"),
    ("clinical_history", "id_historial"),
    ("medications", "id_medicamento"),
    ("patients", "id_paciente"),
]

# Tablas que NUNCA deben tocarse.
PRESERVED = ["users", "roles", "alembic_version"]


def _counts(db) -> dict:
    result = {}
    for table, _ in DELETE_ORDER:
        result[table] = db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
    return result


def _preserved_counts(db) -> dict:
    result = {}
    for table in ("users", "roles"):
        result[table] = db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
    return result


def reset_clinical_data(confirm: bool) -> None:
    if settings.APP_ENV != "development":
        print(
            f"ABORTADO: APP_ENV='{settings.APP_ENV}'. La limpieza solo se permite en 'development'."
        )
        return

    db = SessionLocal()
    try:
        before = _counts(db)
        preserved = _preserved_counts(db)

        print("Entorno: development")
        print("Registros actuales (datos clínicos de desarrollo):")
        for table, _ in DELETE_ORDER:
            print(f"  - {table:<20} {before[table]}")
        print("Se preservan (no se tocan):")
        for table, count in preserved.items():
            print(f"  - {table:<20} {count}")

        if not confirm:
            print("\nModo informativo (dry-run). Para borrar ejecute con --confirm:")
            print("  python -m app.scripts.reset_clinical_data --confirm")
            return

        # Toda la limpieza ocurre en una sola transacción.
        # Fase 1: borrar en orden de llaves foráneas.
        for table, _pk in DELETE_ORDER:
            db.execute(text(f"DELETE FROM {table}"))
        # Fase 2: reiniciar secuencias (solo en desarrollo) una vez que todo se borró.
        # Nota: setval NO es transaccional en Postgres, por eso se ejecuta al final,
        # cuando ya sabemos que los DELETE no fallarán por llaves foráneas.
        for table, pk in DELETE_ORDER:
            seq = db.execute(
                text("SELECT pg_get_serial_sequence(:t, :c)"), {"t": table, "c": pk}
            ).scalar_one_or_none()
            if seq:
                db.execute(text(f"SELECT setval('{seq}', 1, false)"))
        db.commit()

        after = _counts(db)
        print("\nLimpieza completada. Conteos después:")
        for table, _ in DELETE_ORDER:
            print(f"  - {table:<20} {after[table]}")
        print("Intactos:")
        for table, count in _preserved_counts(db).items():
            print(f"  - {table:<20} {count}")
    except Exception:
        db.rollback()
        print("ERROR: se revirtió la transacción; no se borró nada.")
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Limpieza manual de datos clínicos de desarrollo.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirma y ejecuta la limpieza (sin esta bandera solo muestra conteos).",
    )
    args = parser.parse_args()
    reset_clinical_data(confirm=args.confirm)


if __name__ == "__main__":
    main()
