from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.validacion_ia import ValidacionIA
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.dispensacion_repository import DispensacionRepository
from app.repositories.prescription_repository import PrescriptionRepository


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DashboardRepository(db)
        self.prescription_repository = PrescriptionRepository(db)
        self.dispensacion_repository = DispensacionRepository(db)

    def summary(self, inicio: Optional[datetime] = None, fin: Optional[datetime] = None) -> dict:
        usuarios = self.repo.usuarios_por_estado()
        pacientes = self.repo.pacientes_por_estado()
        return {
            "usuarios": {
                "total": self.repo.total_usuarios(),
                "activos": usuarios["activos"],
                "inactivos": usuarios["inactivos"],
            },
            "pacientes": pacientes,
            "recetas": {
                "total": self.repo.total_recetas(inicio, fin),
                "validadas": self.repo.recetas_validadas(inicio, fin),
                "bloqueadas": self.repo.recetas_bloqueadas(),
                "dispensadas": self.repo.recetas_dispensadas(),
                "por_estado": self.repo.recetas_por_estado(inicio, fin),
            },
            "validaciones": {
                "total": self.repo.total_validaciones(inicio, fin),
                "tiempo_promedio_ms": self.repo.tiempo_promedio_ia_ms(inicio, fin),
            },
            "documentos_farmacologicos": self.repo.total_documentos(),
        }

    def recipes(self, inicio=None, fin=None) -> dict:
        return {
            "por_estado": self.repo.recetas_por_estado(inicio, fin),
            "por_fecha": self.repo.recetas_por_fecha(inicio, fin),
            "validadas": self.repo.recetas_validadas(inicio, fin),
            "bloqueadas": self.repo.recetas_bloqueadas(),
            "dispensadas": self.repo.recetas_dispensadas(),
        }

    def alerts(self, inicio=None, fin=None) -> dict:
        return {"por_nivel": self.repo.alertas_por_nivel(inicio, fin)}

    def validations(self, inicio=None, fin=None) -> dict:
        return {
            "total": self.repo.total_validaciones(inicio, fin),
            "tiempo_promedio_ms": self.repo.tiempo_promedio_ia_ms(inicio, fin),
            "por_medico": self.repo.validaciones_por_medico(inicio, fin),
        }

    def medications(self, inicio=None, fin=None) -> dict:
        return {
            "mas_prescritos": self.repo.medicamentos_mas_prescritos(inicio, fin),
            "dispensaciones_por_estado": self.repo.dispensaciones_por_estado(inicio, fin),
        }

    # --- Línea de tiempo de una receta ---
    def recipe_timeline(self, recipe_id: int) -> dict:
        recipe = self.prescription_repository.get_by_id(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Receta no encontrada")

        medico = f"{recipe.medico.nombre} {recipe.medico.apellido}" if recipe.medico else None
        eventos = [
            {"evento": "creacion", "fecha": recipe.fecha_creacion, "usuario": medico, "detalle": "Receta creada"}
        ]

        val = (
            self.db.query(ValidacionIA)
            .filter(ValidacionIA.id_receta == recipe_id)
            .order_by(ValidacionIA.id_validacion.desc())
            .first()
        )
        if val:
            aud = (
                self.db.query(Auditoria)
                .filter(Auditoria.accion == "validacion_ia", Auditoria.id_registro == recipe_id)
                .order_by(Auditoria.id_auditoria.desc())
                .first()
            )
            usuario_val = f"{aud.usuario.nombre} {aud.usuario.apellido}" if aud and aud.usuario else medico
            eventos.append({
                "evento": "validacion", "fecha": val.fecha_validacion, "usuario": usuario_val,
                "detalle": f"Validación IA nivel {val.nivel_riesgo}",
            })

        disp = self.dispensacion_repository.get_latest_for_recipe(recipe_id)
        if disp:
            aud_qr = (
                self.db.query(Auditoria)
                .filter(Auditoria.accion == "qr_generado", Auditoria.id_registro == disp.id_dispensacion)
                .first()
            )
            usuario_qr = f"{aud_qr.usuario.nombre} {aud_qr.usuario.apellido}" if aud_qr and aud_qr.usuario else medico
            eventos.append({
                "evento": "qr_generado", "fecha": disp.fecha_registro, "usuario": usuario_qr,
                "detalle": "Código QR generado",
            })
            if disp.estado in ("confirmada", "rechazada"):
                farm = f"{disp.farmaceutico.nombre} {disp.farmaceutico.apellido}" if disp.farmaceutico else None
                eventos.append({
                    "evento": f"dispensacion_{disp.estado}", "fecha": disp.fecha_dispensacion, "usuario": farm,
                    "detalle": f"Dispensación {disp.estado}",
                })

        return {"id_receta": recipe_id, "eventos": eventos}
