import json
import random

from app.services import ollama_client
from tests.conftest import requires_db

pytestmark = requires_db

VALID_JSON = json.dumps({"resumen": "ok", "interacciones": [], "contraindicaciones": [], "nivel_sugerido": 0})


def _mock_ollama(monkeypatch):
    monkeypatch.setattr(ollama_client, "embed_text", lambda t: [0.1] * 8)
    monkeypatch.setattr(ollama_client, "embed_texts", lambda ts: [[0.1] * 8 for _ in ts])
    monkeypatch.setattr(ollama_client, "chat", lambda system, prompt: VALID_JSON)


def _ci() -> str:
    return f"CI{random.randint(10_000_000, 99_999_999)}"


def _flujo_receta(client, doctor_headers, auth_headers, monkeypatch, dup=False):
    """Crea paciente, medicamento y receta (validada) y devuelve ids."""
    _mock_ollama(monkeypatch)
    pid = client.post("/api/v1/patients", headers=doctor_headers,
                      json={"nombre": "Aud", "apellido": "Dash", "ci": _ci(), "fecha_nacimiento": "1990-01-01"}).json()["id_paciente"]
    med = client.post("/api/v1/medications", headers=auth_headers, json={"nombre": f"Med {random.randint(1,99999)}"}).json()["id_medicamento"]
    items = [{"id_medicamento": med, "dosis": "1", "frecuencia": "8h", "instrucciones": "oral"}]
    if dup:
        items.append({"id_medicamento": med, "dosis": "1", "frecuencia": "12h", "instrucciones": "oral"})
    rid = client.post("/api/v1/prescriptions", headers=doctor_headers, json={"id_paciente": pid, "items": items}).json()["id_receta"]
    client.post(f"/api/v1/prescriptions/{rid}/validate", headers=doctor_headers)
    return pid, med, rid


# --- Auditoría ------------------------------------------------------------------

def test_auditoria_se_crea_automaticamente(client, doctor_headers, auth_headers, monkeypatch):
    _flujo_receta(client, doctor_headers, auth_headers, monkeypatch)
    res = client.get("/api/v1/audit", headers=auth_headers, params={"page_size": 50})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    acciones = {a["accion"] for a in body["items"]}
    # Debe haberse auditado al menos la creación de paciente y la validación IA.
    assert "crear" in acciones or "validacion_ia" in acciones
    # No se exponen contraseñas ni tokens en el detalle.
    for a in body["items"]:
        det = (a["detalle"] or "").lower()
        assert "contrasena" not in det and "password" not in det and "token" not in det


def test_auditoria_filtros_y_paginacion(client, auth_headers):
    res = client.get("/api/v1/audit", headers=auth_headers, params={"modulo": "auth", "page": 1, "page_size": 5})
    assert res.status_code == 200
    body = res.json()
    assert body["page"] == 1 and body["page_size"] == 5
    assert all(a["modulo"] == "auth" for a in body["items"])


def test_auditoria_actions_y_modules(client, auth_headers):
    assert client.get("/api/v1/audit/actions", headers=auth_headers).status_code == 200
    mods = client.get("/api/v1/audit/modules", headers=auth_headers).json()
    assert "auth" in mods


def test_auditoria_solo_admin(client, doctor_headers, pharmacist_headers):
    assert client.get("/api/v1/audit", headers=doctor_headers).status_code == 403
    assert client.get("/api/v1/audit", headers=pharmacist_headers).status_code == 403
    assert client.get("/api/v1/audit").status_code in {401, 403}


# --- Dashboard ------------------------------------------------------------------

def test_dashboard_summary(client, doctor_headers, auth_headers, monkeypatch):
    _flujo_receta(client, doctor_headers, auth_headers, monkeypatch)
    res = client.get("/api/v1/admin/dashboard/summary", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["usuarios"]["total"] >= 4
    assert body["usuarios"]["activos"] + body["usuarios"]["inactivos"] == body["usuarios"]["total"]
    assert body["recetas"]["total"] >= 1
    assert body["recetas"]["validadas"] >= 1


def test_dashboard_recipes_por_estado(client, doctor_headers, auth_headers, monkeypatch):
    _flujo_receta(client, doctor_headers, auth_headers, monkeypatch)
    body = client.get("/api/v1/admin/dashboard/recipes", headers=auth_headers).json()
    estados = {e["estado"] for e in body["por_estado"]}
    assert "active" in estados
    assert isinstance(body["por_fecha"], list) and len(body["por_fecha"]) >= 1


def test_dashboard_alerts_por_nivel(client, doctor_headers, auth_headers, monkeypatch):
    # Receta con medicamento duplicado -> genera alerta nivel 2 al validar/prevalidar.
    _, _, rid = _flujo_receta(client, doctor_headers, auth_headers, monkeypatch, dup=True)
    client.post(f"/api/v1/prescriptions/{rid}/prevalidate", headers=doctor_headers)
    body = client.get("/api/v1/admin/dashboard/alerts", headers=auth_headers).json()
    niveles = {n["nivel"] for n in body["por_nivel"]}
    assert len(niveles) >= 1


def test_dashboard_validations(client, doctor_headers, auth_headers, monkeypatch):
    _flujo_receta(client, doctor_headers, auth_headers, monkeypatch)
    body = client.get("/api/v1/admin/dashboard/validations", headers=auth_headers).json()
    assert body["total"] >= 1
    assert isinstance(body["por_medico"], list)


def test_dashboard_medicamentos_mas_prescritos(client, doctor_headers, auth_headers, monkeypatch):
    _flujo_receta(client, doctor_headers, auth_headers, monkeypatch)
    body = client.get("/api/v1/admin/dashboard/medications", headers=auth_headers).json()
    assert isinstance(body["mas_prescritos"], list) and len(body["mas_prescritos"]) >= 1
    assert all("medicamento" in m and "total" in m for m in body["mas_prescritos"])


def test_dashboard_filtro_fecha(client, auth_headers):
    # Rango en el pasado lejano -> sin recetas en ese rango.
    body = client.get("/api/v1/admin/dashboard/recipes", headers=auth_headers,
                      params={"fecha_inicio": "2000-01-01", "fecha_fin": "2000-12-31"}).json()
    assert body["por_estado"] == [] and body["por_fecha"] == []


def test_dashboard_solo_admin(client, doctor_headers, pharmacist_headers):
    assert client.get("/api/v1/admin/dashboard/summary", headers=doctor_headers).status_code == 403
    assert client.get("/api/v1/admin/dashboard/summary", headers=pharmacist_headers).status_code == 403


# --- Línea de tiempo ------------------------------------------------------------

def test_timeline_de_receta(client, doctor_headers, auth_headers, monkeypatch):
    _, _, rid = _flujo_receta(client, doctor_headers, auth_headers, monkeypatch)
    client.post(f"/api/v1/prescriptions/{rid}/generate-qr", headers=doctor_headers)
    res = client.get(f"/api/v1/prescriptions/{rid}/timeline", headers=doctor_headers)
    assert res.status_code == 200
    eventos = {e["evento"] for e in res.json()["eventos"]}
    assert "creacion" in eventos and "validacion" in eventos and "qr_generado" in eventos
