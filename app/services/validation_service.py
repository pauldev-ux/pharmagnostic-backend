import json
import logging
import re
from collections import Counter

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.alerta_clinica import AlertaClinica
from app.models.user import User
from app.models.validacion_ia import ValidacionIA
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.repositories.validacion_repository import ValidacionRepository
from app.schemas.validacion import DISCLAIMER
from app.services import auditoria_service, ollama_client
from app.services.ollama_client import OllamaError
from app.services.rag_service import RagService

logger = logging.getLogger(__name__)


def _extract_json(texto: str) -> dict:
    t = (texto or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*", "", t).strip()
        if t.endswith("```"):
            t = t[:-3].strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No se encontró un objeto JSON en la respuesta")
    return json.loads(t[start : end + 1])


def _base_token(nombre: str) -> str:
    return nombre.split()[0].lower() if nombre else ""


class ValidationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ValidacionRepository(db)
        self.prescription_repository = PrescriptionRepository(db)
        self.alerta_repository = AlertaRepository(db)
        self.rag = RagService(db)

    def _get_recipe(self, recipe_id: int):
        recipe = self.prescription_repository.get_by_id(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        return recipe

    def list_for_recipe(self, recipe_id: int) -> list[ValidacionIA]:
        self._get_recipe(recipe_id)
        return self.repository.get_by_recipe(recipe_id)

    def get_validation(self, validacion_id: int) -> ValidacionIA:
        validacion = self.repository.get_by_id(validacion_id)
        if not validacion:
            raise HTTPException(status_code=404, detail="Validación no encontrada")
        return validacion

    # --- Reglas determinísticas -------------------------------------------------
    def _deterministic(self, recipe) -> dict:
        items = list(recipe.items)
        paciente = recipe.paciente
        alergias_txt = (paciente.alergias or "").lower() if paciente else ""

        duplicidades = []
        conteo = Counter(item.id_medicamento for item in items)
        for med_id, veces in conteo.items():
            if veces > 1:
                nombre = next(
                    (i.medicamento.nombre for i in items if i.id_medicamento == med_id and i.medicamento),
                    f"#{med_id}",
                )
                duplicidades.append({"medicamento": nombre, "veces": veces, "nivel": 2})

        errores_dosis = []
        for item in items:
            faltantes = []
            if not (item.dosis and str(item.dosis).strip()):
                faltantes.append("dosis")
            if not (item.frecuencia and str(item.frecuencia).strip()):
                faltantes.append("frecuencia")
            if not (item.instrucciones and str(item.instrucciones).strip()):
                faltantes.append("vía/duración")
            if faltantes:
                nombre = item.medicamento.nombre if item.medicamento else f"#{item.id_medicamento}"
                errores_dosis.append({"medicamento": nombre, "faltantes": faltantes, "nivel": 1})

        contraindicaciones = []
        if alergias_txt:
            for item in items:
                if not item.medicamento:
                    continue
                token = _base_token(item.medicamento.nombre)
                if token and token in alergias_txt:
                    contraindicaciones.append(
                        {
                            "descripcion": f"El paciente declara alergia compatible con '{item.medicamento.nombre}'.",
                            "medicamento": item.medicamento.nombre,
                            "fuente": "Registro del paciente (alergias)",
                            "nivel": 3,
                        }
                    )

        # Inconsistencias entre el último audio transcrito y la receta.
        inconsistencias_audio = []
        audio = next(
            (
                a
                for a in sorted(recipe.audios, key=lambda x: x.id_audio, reverse=True)
                if a.estado_procesamiento == "completado" and a.transcripcion
            ),
            None,
        )
        if audio:
            texto = audio.transcripcion.lower()
            vistos = set()
            for item in items:
                if not item.medicamento or item.id_medicamento in vistos:
                    continue
                vistos.add(item.id_medicamento)
                token = _base_token(item.medicamento.nombre)
                if token and token not in texto:
                    inconsistencias_audio.append(
                        {
                            "medicamento": item.medicamento.nombre,
                            "detalle": "No aparece en la transcripción del audio.",
                            "nivel": 2,
                        }
                    )

        otros = []
        if paciente and not paciente.activo:
            otros.append({"tipo": "paciente_inactivo", "descripcion": "El paciente está inactivo.", "nivel": 2})
        for item in items:
            if item.medicamento and item.medicamento.estado != "active":
                otros.append(
                    {
                        "tipo": "medicamento_inactivo",
                        "descripcion": f"El medicamento '{item.medicamento.nombre}' está inactivo.",
                        "nivel": 2,
                    }
                )
        if recipe.id_diagnostico is None:
            otros.append({"tipo": "sin_diagnostico", "descripcion": "La receta no tiene diagnóstico asociado.", "nivel": 1})

        niveles = [0]
        for grupo in (duplicidades, errores_dosis, contraindicaciones, inconsistencias_audio, otros):
            niveles.extend(f.get("nivel", 0) for f in grupo)
        nivel_det = max(niveles)

        return {
            "duplicidades": duplicidades,
            "errores_dosis": errores_dosis,
            "contraindicaciones": contraindicaciones,
            "inconsistencias_audio": inconsistencias_audio,
            "otros": otros,
            "nivel_det": nivel_det,
            "id_audio": audio.id_audio if audio else None,
        }

    # --- RAG --------------------------------------------------------------------
    def _retrieve_context(self, recipe) -> tuple[list[dict], list[dict]]:
        nombres = [i.medicamento.nombre for i in recipe.items if i.medicamento]
        if not nombres:
            return [], []
        query = " ".join(nombres) + " interacciones contraindicaciones dosis alergias"
        try:
            fragmentos = self.rag.search(query)
        except HTTPException as exc:
            if exc.status_code == 503:  # Ollama no disponible para embeddings
                logger.warning("RAG no disponible durante la validación: %s", exc.detail)
                return [], []
            raise

        fuentes: dict[int, dict] = {}
        for f in fragmentos:
            fuentes.setdefault(
                f["id_documento"],
                {"id_documento": f["id_documento"], "documento": f["documento"], "fuente": f["fuente"], "version": f["version"]},
            )
        return fragmentos, list(fuentes.values())

    # --- LLM --------------------------------------------------------------------
    def _llm_analysis(self, recipe, deterministic: dict, fragmentos: list[dict]) -> dict:
        paciente = recipe.paciente
        meds = "; ".join(
            f"{i.medicamento.nombre if i.medicamento else i.id_medicamento} "
            f"(dosis={i.dosis or 'N/D'}, frecuencia={i.frecuencia or 'N/D'}, instrucciones={i.instrucciones or 'N/D'})"
            for i in recipe.items
        )
        contexto = "\n\n".join(
            f"[{f['documento']} | {f['fuente'] or 'N/D'} | v{f['version'] or 'N/D'}]\n{f['contenido']}"
            for f in fragmentos
        ) or "SIN DOCUMENTOS RECUPERADOS"

        audio_txt = next(
            (a.transcripcion for a in recipe.audios if a.estado_procesamiento == "completado" and a.transcripcion),
            "Sin transcripción",
        )

        system = (
            "Eres un farmacólogo clínico de APOYO. Analiza la receta usando ÚNICAMENTE el CONTEXTO "
            "documental recuperado y los DATOS. NO inventes interacciones ni contraindicaciones: cada "
            "una DEBE citar una fuente presente en el CONTEXTO. Si no hay soporte documental, deja las "
            "listas vacías. Responde EXCLUSIVAMENTE con un objeto JSON válido, sin texto adicional, con "
            "las claves: resumen (string), interacciones (array de objetos {descripcion, fuente}), "
            "contraindicaciones (array de objetos {descripcion, fuente}), nivel_sugerido (entero 0 a 3)."
        )
        prompt = (
            f"DATOS DEL PACIENTE:\n"
            f"- Alergias: {paciente.alergias or 'ninguna registrada'}\n"
            f"- Función renal: {paciente.funcion_renal}\n"
            f"- Función hepática: {paciente.funcion_hepatica}\n"
            f"- Activo: {paciente.activo}\n\n"
            f"DIAGNÓSTICO: {'sí' if recipe.id_diagnostico else 'no registrado'}\n\n"
            f"MEDICAMENTOS:\n{meds}\n\n"
            f"TRANSCRIPCIÓN DEL AUDIO:\n{audio_txt}\n\n"
            f"HALLAZGOS DETERMINÍSTICOS (referencia):\n"
            f"- duplicidades: {deterministic['duplicidades']}\n"
            f"- errores_dosis: {deterministic['errores_dosis']}\n"
            f"- contraindicaciones_por_alergia: {deterministic['contraindicaciones']}\n\n"
            f"CONTEXTO DOCUMENTAL (RAG):\n{contexto}\n\n"
            f"Devuelve solo el JSON."
        )

        import time

        inicio = time.perf_counter()
        try:
            respuesta = ollama_client.chat(system, prompt)
        except OllamaError:
            raise HTTPException(status_code=503, detail="Ollama no disponible para la validación con IA")
        duracion_ms = int((time.perf_counter() - inicio) * 1000)

        try:
            data = _extract_json(respuesta)
        except (ValueError, json.JSONDecodeError):
            logger.error("La IA devolvió una respuesta no-JSON: %s", respuesta[:300])
            raise HTTPException(status_code=502, detail="La IA devolvió una respuesta inválida (se exige JSON)")

        return {
            "resumen": str(data.get("resumen", "")).strip(),
            "interacciones": self._normalizar_lista(data.get("interacciones")),
            "contraindicaciones": self._normalizar_lista(data.get("contraindicaciones")),
            "nivel_sugerido": int(data.get("nivel_sugerido", 0) or 0),
            "duracion_ms": duracion_ms,
        }

    @classmethod
    def _normalizar_lista(cls, items) -> list[dict]:
        # Normaliza y descarta ítems vacíos que el LLM ocasionalmente devuelve.
        normalizados = [cls._normalizar_item(i) for i in (items or [])]
        return [n for n in normalizados if n["descripcion"]]

    @staticmethod
    def _normalizar_item(item) -> dict:
        """Normaliza las claves del LLM (acepta variantes en inglés) a descripcion/fuente."""
        if not isinstance(item, dict):
            return {"descripcion": str(item), "fuente": ""}
        descripcion = item.get("descripcion") or item.get("description") or item.get("detalle") or ""
        fuente = item.get("fuente") or item.get("source") or item.get("documento") or ""
        return {"descripcion": str(descripcion).strip(), "fuente": str(fuente).strip()}

    # --- Orquestación -----------------------------------------------------------
    def validate(self, recipe_id: int, current_user: User) -> dict:
        recipe = self._get_recipe(recipe_id)

        deterministic = self._deterministic(recipe)
        fragmentos, fuentes_rag = self._retrieve_context(recipe)
        llm = self._llm_analysis(recipe, deterministic, fragmentos)

        nivel_llm = max(0, min(3, llm["nivel_sugerido"]))
        nivel_final = max(deterministic["nivel_det"], nivel_llm)

        # contraindicaciones = alergias (determinístico) + RAG (IA).
        contraindicaciones = list(deterministic["contraindicaciones"]) + list(llm["contraindicaciones"])

        resumen_det = self._resumen_deterministico(deterministic)
        resumen = (llm["resumen"] + ("\n\n" + resumen_det if resumen_det else "")).strip() or resumen_det

        validacion = ValidacionIA(
            id_receta=recipe_id,
            id_audio=deterministic["id_audio"],
            nivel_riesgo=nivel_final,
            duracion_ms=llm.get("duracion_ms"),
            resumen=resumen,
            interacciones=llm["interacciones"],
            contraindicaciones=contraindicaciones,
            duplicidades=deterministic["duplicidades"],
            errores_dosis=deterministic["errores_dosis"],
            inconsistencias_audio=deterministic["inconsistencias_audio"],
            fuentes_rag=fuentes_rag,
        )
        self.repository.add(validacion)

        # Crear alertas (reemplazando las anteriores de la receta).
        self.alerta_repository.delete_by_recipe(recipe_id)
        self._crear_alertas(recipe_id, deterministic, contraindicaciones, llm["interacciones"])

        # Actualizar nivel de riesgo y estado de bloqueo de la receta.
        recipe.nivel_riesgo = nivel_final
        recipe.bloqueada = nivel_final >= 3
        # Una nueva validación que baja el riesgo limpia la justificación previa.
        if nivel_final < 3:
            recipe.justificacion = None

        auditoria_service.registrar(
            self.db, accion="validacion_ia", modulo="validacion", tabla_afectada="prescriptions",
            id_registro=recipe_id, detalle=f"Validación IA nivel {nivel_final}",
            user_id=current_user.id_usuario,
        )
        self.db.commit()
        self.db.refresh(validacion)

        result = {c.name: getattr(validacion, c.name) for c in validacion.__table__.columns}
        result["bloqueada"] = recipe.bloqueada
        result["mensaje"] = DISCLAIMER
        return result

    @staticmethod
    def _resumen_deterministico(deterministic: dict) -> str:
        partes = []
        if deterministic["duplicidades"]:
            partes.append(f"{len(deterministic['duplicidades'])} duplicidad(es)")
        if deterministic["errores_dosis"]:
            partes.append(f"{len(deterministic['errores_dosis'])} con datos de dosificación incompletos")
        if deterministic["contraindicaciones"]:
            partes.append(f"{len(deterministic['contraindicaciones'])} alerta(s) por alergia")
        if deterministic["inconsistencias_audio"]:
            partes.append(f"{len(deterministic['inconsistencias_audio'])} inconsistencia(s) con el audio")
        for o in deterministic["otros"]:
            partes.append(o["descripcion"])
        return ("Reglas internas: " + "; ".join(partes) + ".") if partes else "Reglas internas: sin hallazgos."

    def _crear_alertas(self, recipe_id, deterministic, contraindicaciones, interacciones):
        alertas: list[AlertaClinica] = []
        for d in deterministic["duplicidades"]:
            alertas.append(
                AlertaClinica(
                    id_receta=recipe_id, tipo_alerta="ia_duplicidad", nivel=2,
                    descripcion=f"Medicamento duplicado: '{d['medicamento']}' ({d['veces']} veces).",
                    recomendacion="Verifique la repetición del medicamento.",
                )
            )
        for e in deterministic["errores_dosis"]:
            alertas.append(
                AlertaClinica(
                    id_receta=recipe_id, tipo_alerta="ia_dosis", nivel=1,
                    descripcion=f"Datos incompletos ({', '.join(e['faltantes'])}) en '{e['medicamento']}'.",
                    recomendacion="Complete dosis, frecuencia, vía y duración.",
                )
            )
        for c in contraindicaciones:
            alertas.append(
                AlertaClinica(
                    id_receta=recipe_id, tipo_alerta="ia_contraindicacion",
                    nivel=int(c.get("nivel", 3)),
                    descripcion=c.get("descripcion", "Posible contraindicación."),
                    recomendacion=f"Fuente: {c.get('fuente', 'N/D')}.",
                )
            )
        for i in deterministic["inconsistencias_audio"]:
            alertas.append(
                AlertaClinica(
                    id_receta=recipe_id, id_audio=deterministic["id_audio"],
                    tipo_alerta="ia_inconsistencia_audio", nivel=2,
                    descripcion=f"{i['medicamento']}: {i['detalle']}",
                    recomendacion="Revise el audio frente a la receta.",
                )
            )
        for o in deterministic["otros"]:
            alertas.append(
                AlertaClinica(
                    id_receta=recipe_id, tipo_alerta=f"ia_{o['tipo']}", nivel=int(o.get("nivel", 1)),
                    descripcion=o["descripcion"], recomendacion="Revisión médica recomendada.",
                )
            )
        for inter in interacciones:
            if isinstance(inter, dict) and inter.get("descripcion"):
                alertas.append(
                    AlertaClinica(
                        id_receta=recipe_id, tipo_alerta="ia_interaccion", nivel=2,
                        descripcion=inter.get("descripcion"),
                        recomendacion=f"Fuente: {inter.get('fuente', 'N/D')}.",
                    )
                )
        self.alerta_repository.add_all(alertas)

    def justificar(self, recipe_id: int, justificacion: str, current_user: User) -> dict:
        recipe = self._get_recipe(recipe_id)
        recipe.justificacion = justificacion
        recipe.bloqueada = False
        auditoria_service.registrar(
            self.db, accion="alerta_justificada", modulo="validacion", tabla_afectada="prescriptions",
            id_registro=recipe_id, detalle="Receta justificada (desbloqueada)",
            user_id=current_user.id_usuario,
        )
        self.db.commit()
        return {"id_receta": recipe_id, "bloqueada": False, "justificacion": justificacion}
