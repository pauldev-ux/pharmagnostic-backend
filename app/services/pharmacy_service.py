from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.dispensacion import Dispensacion
from app.models.user import User
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.dispensacion_repository import DispensacionRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.services import qr_service
from app.services.prescription_service import PrescriptionService


def _serialize_alerta(a) -> dict:
    return {
        "id_alerta": a.id_alerta,
        "tipo_alerta": a.tipo_alerta,
        "nivel": a.nivel,
        "descripcion": a.descripcion,
        "recomendacion": a.recomendacion,
        "revisada": a.revisada,
    }


class PharmacyService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = DispensacionRepository(db)
        self.prescription_repository = PrescriptionRepository(db)
        self.alerta_repository = AlertaRepository(db)

    def _get_recipe(self, recipe_id: int):
        recipe = self.prescription_repository.get_by_id(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        return recipe

    # --- Generación de QR (médico) ---
    def generate_qr(self, recipe_id: int, current_user: User) -> dict:
        recipe = self._get_recipe(recipe_id)

        if not recipe.validaciones:
            raise HTTPException(status_code=400, detail="La receta debe validarse antes de generar el QR")
        if recipe.bloqueada:
            raise HTTPException(status_code=400, detail="La receta está bloqueada por riesgo crítico")
        if recipe.estado == "cancelled":
            raise HTTPException(status_code=400, detail="La receta está anulada")
        if recipe.estado == "dispensada":
            raise HTTPException(status_code=400, detail="La receta ya fue dispensada")

        # No generar varios QR activos para la misma receta.
        dispensacion = self.repository.get_pending_for_recipe(recipe_id)
        if not dispensacion:
            dispensacion = Dispensacion(
                id_receta=recipe_id,
                codigo_verificacion=qr_service.generate_token(),
                estado="pendiente",
            )
            self.repository.create(dispensacion)

        url = qr_service.verification_url(dispensacion.codigo_verificacion)
        return {
            "id_dispensacion": dispensacion.id_dispensacion,
            "id_receta": recipe_id,
            "codigo_verificacion": dispensacion.codigo_verificacion,
            "url_verificacion": url,
            "qr_base64": qr_service.generate_qr_base64(url),
            "estado": dispensacion.estado,
        }

    # --- Consulta (farmacéutico / médico / admin) ---
    def list_recipes(self, estado: str | None = None, search: str | None = None) -> list[dict]:
        dispensaciones = self.repository.list_all(estado=estado)
        items = []
        term = (search or "").strip().lower()
        for d in dispensaciones:
            r = d.receta
            paciente = f"{r.paciente.nombre} {r.paciente.apellido}" if r and r.paciente else None
            medico = f"{r.medico.nombre} {r.medico.apellido}" if r and r.medico else None
            item = {
                "id_receta": d.id_receta,
                "id_dispensacion": d.id_dispensacion,
                "codigo_verificacion": d.codigo_verificacion,
                "estado_dispensacion": d.estado,
                "estado_receta": r.estado if r else None,
                "paciente_nombre": paciente,
                "medico_nombre": medico,
                "nivel_riesgo": r.nivel_riesgo if r else 0,
                "fecha_emision": r.fecha_emision if r else None,
                "fecha_registro": d.fecha_registro,
            }
            if term:
                blob = " ".join(
                    str(x).lower()
                    for x in (d.codigo_verificacion, paciente, item["fecha_emision"])
                    if x
                )
                if term not in blob:
                    continue
            items.append(item)
        return items

    def recipe_detail(self, recipe_id: int) -> dict:
        recipe = self._get_recipe(recipe_id)
        dispensacion = self.repository.get_latest_for_recipe(recipe_id)
        alertas = self.alerta_repository.get_by_recipe(recipe_id)
        return {
            "receta": PrescriptionService.serialize(recipe),
            "dispensacion": dispensacion,
            "alertas": [_serialize_alerta(a) for a in alertas],
            "validada": len(recipe.validaciones) > 0,
        }

    # --- Verificación de QR ---
    def verify_qr(self, codigo: str) -> dict:
        token = qr_service.extract_token(codigo)
        dispensacion = self.repository.get_by_codigo(token)
        if not dispensacion:
            return {"estado_qr": "invalido", "mensaje": "Código de verificación no encontrado."}

        recipe = dispensacion.receta
        base = {"id_receta": dispensacion.id_receta, "id_dispensacion": dispensacion.id_dispensacion}

        if dispensacion.estado == "confirmada" or (recipe and recipe.estado == "dispensada"):
            return {"estado_qr": "usado", "mensaje": "El código ya fue utilizado (receta dispensada).", **base}
        if dispensacion.estado == "rechazada":
            return {"estado_qr": "anulado", "mensaje": "La dispensación fue rechazada.", **base}
        if recipe and recipe.estado == "cancelled":
            return {"estado_qr": "anulado", "mensaje": "La receta está anulada.", **base}
        if recipe and recipe.bloqueada:
            return {"estado_qr": "anulado", "mensaje": "La receta está bloqueada por riesgo crítico.", **base}
        return {"estado_qr": "valido", "mensaje": "Código válido. Receta lista para dispensar.", **base}

    # --- Dispensar / rechazar (farmacéutico) ---
    def _resolve_pending(self, recipe_id: int, codigo: str | None):
        if codigo:
            dispensacion = self.repository.get_by_codigo(qr_service.extract_token(codigo))
            if dispensacion and dispensacion.id_receta != recipe_id:
                raise HTTPException(status_code=400, detail="El código no corresponde a esta receta")
        else:
            dispensacion = self.repository.get_pending_for_recipe(recipe_id)
        return dispensacion

    def dispense(self, recipe_id: int, codigo: str | None, observaciones: str | None, current_user: User) -> Dispensacion:
        recipe = self._get_recipe(recipe_id)
        dispensacion = self._resolve_pending(recipe_id, codigo)

        if not dispensacion:
            raise HTTPException(status_code=400, detail="No existe un QR pendiente para esta receta")
        if dispensacion.estado == "confirmada" or recipe.estado == "dispensada":
            raise HTTPException(status_code=400, detail="La receta ya fue dispensada")
        if dispensacion.estado == "rechazada":
            raise HTTPException(status_code=400, detail="La dispensación fue rechazada")
        if recipe.estado == "cancelled":
            raise HTTPException(status_code=400, detail="No se puede dispensar una receta anulada")
        if recipe.bloqueada:
            raise HTTPException(status_code=400, detail="No se puede dispensar una receta bloqueada")

        dispensacion.estado = "confirmada"
        dispensacion.id_usuario_farmaceutico = current_user.id_usuario
        dispensacion.observaciones = observaciones
        dispensacion.fecha_dispensacion = datetime.utcnow()
        recipe.estado = "dispensada"
        self.db.commit()
        self.db.refresh(dispensacion)
        return dispensacion

    def reject(self, recipe_id: int, observaciones: str, current_user: User) -> Dispensacion:
        self._get_recipe(recipe_id)
        dispensacion = self.repository.get_pending_for_recipe(recipe_id)
        if not dispensacion:
            raise HTTPException(status_code=400, detail="No existe un QR pendiente para esta receta")

        dispensacion.estado = "rechazada"
        dispensacion.id_usuario_farmaceutico = current_user.id_usuario
        dispensacion.observaciones = observaciones
        dispensacion.fecha_dispensacion = datetime.utcnow()
        self.db.commit()
        self.db.refresh(dispensacion)
        return dispensacion
