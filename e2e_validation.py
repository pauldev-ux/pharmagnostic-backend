"""Prueba de validación de extremo a extremo con Ollama real.

Requiere: backend en :8000, Ollama en :11434 con nomic-embed-text y llama3.
Uso: python e2e_validation.py
"""

import json
import random

import httpx

B = "http://localhost:8000/api/v1"
c = httpx.Client(base_url=B, timeout=600)


def login(u):
    r = c.post("/auth/login", json={"username": u, "contrasena": "123456"})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main():
    adm = login("admin")
    doc = login("doctor")

    # 1) Cargar y procesar el documento farmacológico (embeddings reales con Ollama).
    with open("sample_docs/vademecum_demo.txt", "rb") as fh:
        contenido = fh.read()
    up = c.post(
        "/pharmacological-documents",
        headers=adm,
        files={"file": (f"vademecum_{random.randint(1,99999)}.txt", contenido, "text/plain")},
        data={"titulo": "Vademécum demo", "fuente": "Guía interna", "version": "2024"},
    )
    print("Cargar documento:", up.status_code)
    did = up.json()["id_documento"]
    proc = c.post(f"/pharmacological-documents/{did}/process", headers=adm)
    print("Procesar (embeddings):", proc.status_code, proc.json())

    # 2) Búsqueda semántica de prueba.
    s = c.post(
        "/pharmacological-knowledge/search",
        headers=doc,
        json={"query": "interacción warfarina ibuprofeno sangrado", "top_k": 3},
    )
    print("\nBúsqueda semántica top-1:", json.dumps(s.json()[0], ensure_ascii=False)[:300] if s.json() else "vacío")

    # 3) Receta con interacción (warfarina + ibuprofeno) -> el LLM debe detectarla con RAG.
    pid = c.post(
        "/patients", headers=doc,
        json={"nombre": "Mario", "apellido": "Soto", "ci": f"CI{random.randint(10**7,10**8)}",
              "fecha_nacimiento": "1960-04-12", "funcion_renal": "moderada"},
    ).json()["id_paciente"]
    dxid = c.post(f"/patients/{pid}/diagnoses", headers=doc, json={"descripcion": "Tromboembolismo"}).json()["id_diagnostico"]
    warf = c.post("/medications", headers=adm, json={"nombre": "Warfarina"}).json()["id_medicamento"]
    ibu = c.post("/medications", headers=adm, json={"nombre": "Ibuprofeno"}).json()["id_medicamento"]
    rx = c.post("/prescriptions", headers=doc, json={
        "id_paciente": pid, "id_diagnostico": dxid,
        "items": [
            {"id_medicamento": warf, "dosis": "5mg", "frecuencia": "24h", "instrucciones": "oral, 30 días"},
            {"id_medicamento": ibu, "dosis": "400mg", "frecuencia": "8h", "instrucciones": "oral, 5 días"},
        ],
    }).json()
    rid = rx["id_receta"]
    print(f"\nReceta #{rid} (warfarina + ibuprofeno) creada.")

    val = c.post(f"/prescriptions/{rid}/validate", headers=doc)
    print("VALIDAR:", val.status_code)
    body = val.json()
    print("  nivel_riesgo:", body["nivel_riesgo"], "| bloqueada:", body["bloqueada"])
    print("  resumen:", body["resumen"])
    print("  interacciones:", json.dumps(body["interacciones"], ensure_ascii=False))
    print("  contraindicaciones:", json.dumps(body["contraindicaciones"], ensure_ascii=False))
    print("  fuentes_rag:", json.dumps(body["fuentes_rag"], ensure_ascii=False))

    # 4) Caso de alergia -> nivel 3 y bloqueo.
    pid2 = c.post(
        "/patients", headers=doc,
        json={"nombre": "Lucía", "apellido": "Ríos", "ci": f"CI{random.randint(10**7,10**8)}",
              "fecha_nacimiento": "1985-08-01", "alergias": "amoxicilina, penicilina"},
    ).json()["id_paciente"]
    amox = c.post("/medications", headers=adm, json={"nombre": "Amoxicilina"}).json()["id_medicamento"]
    rx2 = c.post("/prescriptions", headers=doc, json={
        "id_paciente": pid2,
        "items": [{"id_medicamento": amox, "dosis": "500mg", "frecuencia": "8h", "instrucciones": "oral, 7 días"}],
    }).json()
    rid2 = rx2["id_receta"]
    val2 = c.post(f"/prescriptions/{rid2}/validate", headers=doc).json()
    print(f"\nReceta #{rid2} (alergia a amoxicilina): nivel", val2["nivel_riesgo"], "| bloqueada:", val2["bloqueada"])
    receta2 = c.get(f"/prescriptions/{rid2}", headers=doc).json()
    print("  receta.bloqueada:", receta2["bloqueada"])
    just = c.patch(f"/prescriptions/{rid2}/justify", headers=doc, json={"justificacion": "Riesgo evaluado, se vigilará."})
    print("  justificar -> bloqueada:", just.json()["bloqueada"])

    print("\nE2E OK")


if __name__ == "__main__":
    main()
