from collections import Counter

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.alerta_clinica import AlertaClinica
from app.models.user import User
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.audio_repository import AudioRepository
from app.repositories.prescription_repository import PrescriptionRepository


class AlertaService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AlertaRepository(db)
        self.prescription_repository = PrescriptionRepository(db)
        self.audio_repository = AudioRepository(db)

    def _ensure_recipe(self, recipe_id: int):
        recipe = self.prescription_repository.get_by_id(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        return recipe

    def list_for_recipe(self, recipe_id: int) -> list[AlertaClinica]:
        self._ensure_recipe(recipe_id)
        return self.repository.get_by_recipe(recipe_id)

    def review(self, alerta_id: int, revisada: bool, current_user: User) -> AlertaClinica:
        alerta = self.repository.get_by_id(alerta_id)
        if not alerta:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")
        alerta.revisada = revisada
        return self.repository.save(alerta)

    def _build_alerts(self, recipe) -> list[AlertaClinica]:
        """Aplica reglas determinísticas iniciales y devuelve las alertas (sin persistir)."""
        alertas: list[AlertaClinica] = []
        items = list(recipe.items)

        # Regla nivel 1: dosis o frecuencia faltante en algún ítem.
        for item in items:
            faltantes = []
            if not (item.dosis and str(item.dosis).strip()):
                faltantes.append("dosis")
            if not (item.frecuencia and str(item.frecuencia).strip()):
                faltantes.append("frecuencia")
            if faltantes:
                nombre = item.medicamento.nombre if item.medicamento else f"medicamento #{item.id_medicamento}"
                alertas.append(
                    AlertaClinica(
                        id_receta=recipe.id_receta,
                        tipo_alerta="campos_incompletos",
                        nivel=1,
                        descripcion=f"Faltan datos ({', '.join(faltantes)}) en el medicamento '{nombre}'.",
                        recomendacion="Complete dosis y frecuencia antes de validar definitivamente.",
                    )
                )

        # Regla nivel 2: medicamento repetido dentro de la misma receta.
        conteo = Counter(item.id_medicamento for item in items)
        for med_id, veces in conteo.items():
            if veces > 1:
                nombre = next(
                    (i.medicamento.nombre for i in items if i.id_medicamento == med_id and i.medicamento),
                    f"medicamento #{med_id}",
                )
                alertas.append(
                    AlertaClinica(
                        id_receta=recipe.id_receta,
                        tipo_alerta="medicamento_duplicado",
                        nivel=2,
                        descripcion=f"El medicamento '{nombre}' aparece {veces} veces en la receta.",
                        recomendacion="Verifique si la repetición es intencional o un error de registro.",
                    )
                )

        # Regla nivel 2: diferencia evidente entre la transcripción y los datos registrados.
        audios = self.audio_repository.get_by_recipe(recipe.id_receta)
        audio_transcrito = next(
            (a for a in audios if a.estado_procesamiento == "completado" and a.transcripcion),
            None,
        )
        if audio_transcrito:
            texto = audio_transcrito.transcripcion.lower()
            vistos = set()
            for item in items:
                if not item.medicamento or item.id_medicamento in vistos:
                    continue
                vistos.add(item.id_medicamento)
                base = item.medicamento.nombre.split()[0].lower() if item.medicamento.nombre else ""
                if base and base not in texto:
                    alertas.append(
                        AlertaClinica(
                            id_receta=recipe.id_receta,
                            id_audio=audio_transcrito.id_audio,
                            tipo_alerta="diferencia_transcripcion",
                            nivel=2,
                            descripcion=(
                                f"El medicamento '{item.medicamento.nombre}' no aparece en la "
                                f"transcripción del audio."
                            ),
                            recomendacion="Revise el audio y los datos registrados para confirmar la consistencia.",
                        )
                    )

        # Nota: el nivel 3 (riesgo crítico) se conserva como soporte pero NO se genera
        # automáticamente hasta implementar el motor farmacológico del siguiente bloque.
        return alertas

    def prevalidate(self, recipe_id: int, current_user: User) -> dict:
        recipe = self._ensure_recipe(recipe_id)

        # 1) eliminar alertas preliminares anteriores.
        self.repository.delete_by_recipe(recipe_id)

        # 2-3) revisar la receta y generar alertas.
        alertas = self._build_alerts(recipe)
        self.repository.add_all(alertas)

        # 4-5) calcular el nivel máximo y guardarlo en la receta.
        nivel_maximo = max((a.nivel for a in alertas), default=0)
        recipe.nivel_riesgo = nivel_maximo

        self.db.commit()

        # 6) devolver el resumen (recargando las alertas persistidas).
        guardadas = self.repository.get_by_recipe(recipe_id)
        return {
            "id_receta": recipe_id,
            "nivel_maximo": nivel_maximo,
            "total_alertas": len(guardadas),
            "alertas": guardadas,
        }
