from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alerta_clinica import AlertaClinica
from app.models.auditoria import Auditoria
from app.models.dispensacion import Dispensacion
from app.models.documento_farmacologico import DocumentoFarmacologico
from app.models.medication import Medication
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem
from app.models.user import User
from app.models.validacion_ia import ValidacionIA


class DashboardRepository:
    """Consultas agregadas (no carga todos los registros: usa COUNT/GROUP BY/AVG)."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _rango(query, columna, inicio: Optional[datetime], fin: Optional[datetime]):
        if inicio:
            query = query.filter(columna >= inicio)
        if fin:
            query = query.filter(columna <= fin)
        return query

    # --- Totales / resumen ---
    def total_usuarios(self) -> int:
        return self.db.query(func.count(User.id_usuario)).scalar() or 0

    def usuarios_por_estado(self) -> dict:
        activos = self.db.query(func.count(User.id_usuario)).filter(User.activo.is_(True)).scalar() or 0
        inactivos = self.db.query(func.count(User.id_usuario)).filter(User.activo.is_(False)).scalar() or 0
        return {"activos": activos, "inactivos": inactivos}

    def pacientes_por_estado(self) -> dict:
        total = self.db.query(func.count(Patient.id_paciente)).scalar() or 0
        activos = self.db.query(func.count(Patient.id_paciente)).filter(Patient.activo.is_(True)).scalar() or 0
        return {"total": total, "activos": activos, "inactivos": total - activos}

    def total_documentos(self) -> int:
        return self.db.query(func.count(DocumentoFarmacologico.id_documento)).scalar() or 0

    # --- Recetas ---
    def recetas_por_estado(self, inicio=None, fin=None) -> list[dict]:
        q = self.db.query(Prescription.estado, func.count(Prescription.id_receta))
        q = self._rango(q, Prescription.fecha_creacion, inicio, fin)
        return [{"estado": e, "total": t} for e, t in q.group_by(Prescription.estado).all()]

    def recetas_por_fecha(self, inicio=None, fin=None) -> list[dict]:
        fecha = func.date(Prescription.fecha_creacion)
        q = self.db.query(fecha.label("fecha"), func.count(Prescription.id_receta))
        q = self._rango(q, Prescription.fecha_creacion, inicio, fin)
        rows = q.group_by(fecha).order_by(fecha).all()
        return [{"fecha": str(f), "total": t} for f, t in rows]

    def total_recetas(self, inicio=None, fin=None) -> int:
        q = self._rango(self.db.query(func.count(Prescription.id_receta)), Prescription.fecha_creacion, inicio, fin)
        return q.scalar() or 0

    def recetas_validadas(self, inicio=None, fin=None) -> int:
        q = self.db.query(func.count(func.distinct(ValidacionIA.id_receta)))
        q = self._rango(q, ValidacionIA.fecha_validacion, inicio, fin)
        return q.scalar() or 0

    def recetas_bloqueadas(self) -> int:
        return self.db.query(func.count(Prescription.id_receta)).filter(Prescription.bloqueada.is_(True)).scalar() or 0

    def recetas_dispensadas(self) -> int:
        return self.db.query(func.count(Prescription.id_receta)).filter(Prescription.estado == "dispensada").scalar() or 0

    # --- Alertas ---
    def alertas_por_nivel(self, inicio=None, fin=None) -> list[dict]:
        q = self.db.query(AlertaClinica.nivel, func.count(AlertaClinica.id_alerta))
        q = self._rango(q, AlertaClinica.fecha_generacion, inicio, fin)
        rows = q.group_by(AlertaClinica.nivel).order_by(AlertaClinica.nivel).all()
        return [{"nivel": n, "total": t} for n, t in rows]

    # --- Validaciones ---
    def validaciones_por_medico(self, inicio=None, fin=None) -> list[dict]:
        # Se usa la auditoría (registra quién validó).
        q = self.db.query(
            User.id_usuario,
            func.concat(User.nombre, " ", User.apellido).label("medico"),
            func.count(Auditoria.id_auditoria),
        ).join(User, Auditoria.id_usuario == User.id_usuario).filter(Auditoria.accion == "validacion_ia")
        q = self._rango(q, Auditoria.fecha_accion, inicio, fin)
        rows = q.group_by(User.id_usuario, User.nombre, User.apellido).all()
        return [{"id_usuario": uid, "medico": m, "total": t} for uid, m, t in rows]

    def total_validaciones(self, inicio=None, fin=None) -> int:
        q = self._rango(self.db.query(func.count(ValidacionIA.id_validacion)), ValidacionIA.fecha_validacion, inicio, fin)
        return q.scalar() or 0

    def tiempo_promedio_ia_ms(self, inicio=None, fin=None) -> Optional[float]:
        q = self._rango(self.db.query(func.avg(ValidacionIA.duracion_ms)), ValidacionIA.fecha_validacion, inicio, fin)
        avg = q.scalar()
        return round(float(avg), 1) if avg is not None else None

    # --- Medicamentos / dispensaciones ---
    def medicamentos_mas_prescritos(self, inicio=None, fin=None, limit: int = 10) -> list[dict]:
        q = self.db.query(
            Medication.nombre, func.count(PrescriptionItem.id_item).label("total")
        ).join(PrescriptionItem, PrescriptionItem.id_medicamento == Medication.id_medicamento)
        if inicio or fin:
            q = q.join(Prescription, Prescription.id_receta == PrescriptionItem.id_receta)
            q = self._rango(q, Prescription.fecha_creacion, inicio, fin)
        rows = q.group_by(Medication.nombre).order_by(func.count(PrescriptionItem.id_item).desc()).limit(limit).all()
        return [{"medicamento": n, "total": t} for n, t in rows]

    def dispensaciones_por_estado(self, inicio=None, fin=None) -> list[dict]:
        q = self.db.query(Dispensacion.estado, func.count(Dispensacion.id_dispensacion))
        q = self._rango(q, Dispensacion.fecha_registro, inicio, fin)
        return [{"estado": e, "total": t} for e, t in q.group_by(Dispensacion.estado).all()]
