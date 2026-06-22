"""E2E completo: el ADMIN ejecuta todas las funciones; el paciente usa su cuenta creada.

Requiere backend en :8000 y Ollama en :11434 (validación y chatbot reales).
"""

import random

import httpx

B = "http://localhost:8000/api/v1"
c = httpx.Client(base_url=B, timeout=600)


def login(u, p="123456"):
    r = c.post("/auth/login", json={"username": u, "contrasena": p})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def ok(label, resp, expected=200):
    code = resp.status_code if hasattr(resp, "status_code") else resp
    print(f"  [{'OK' if code == expected else 'XX'}] {label}: {code}")
    return resp


def main():
    adm = login("admin")
    suf = random.randint(1000, 9999)
    print("== ADMIN hace TODO ==")

    # 1) Admin registra paciente CREANDO su cuenta de acceso (usuario + contraseña).
    uname = f"pac{suf}"
    r = c.post("/patients", headers=adm, json={
        "nombre": "Ana", "apellido": "Lopez", "ci": f"CI{random.randint(10**7,10**8)}",
        "fecha_nacimiento": "1985-06-15", "funcion_renal": "moderada",
        "username": uname, "password": "clave123",
    })
    ok("admin crea paciente + cuenta", r, 201)
    pid = r.json()["id_paciente"]

    # 2) Admin: diagnóstico e historial clínico (superusuario).
    dx = ok("admin crea diagnóstico", c.post(f"/patients/{pid}/diagnoses", headers=adm, json={"descripcion": "Hipertensión"}), 201).json()["id_diagnostico"]
    ok("admin crea historial", c.post(f"/patients/{pid}/clinical-history", headers=adm, json={"tipo_evento": "antecedente", "descripcion": "HTA familiar"}), 201)

    # 3) Admin: medicamento y receta.
    med = c.post("/medications", headers=adm, json={"nombre": f"Enalapril {suf}"}).json()["id_medicamento"]
    rid = c.post("/prescriptions", headers=adm, json={
        "id_paciente": pid, "id_diagnostico": dx,
        "items": [{"id_medicamento": med, "dosis": "10mg", "frecuencia": "24h", "instrucciones": "oral, 30 días"}],
    }).json()["id_receta"]
    print(f"  receta #{rid} creada por admin")

    # 4) Admin: validación inteligente (Llama 3).
    val = ok("admin valida receta", c.post(f"/prescriptions/{rid}/validate", headers=adm)).json()
    print(f"     nivel_riesgo={val['nivel_riesgo']} bloqueada={val['bloqueada']}")

    # 5) Admin: audio (subida) + alerta preliminar.
    ok("admin sube audio", c.post(f"/prescriptions/{rid}/audios", headers=adm, files={"file": ("a.webm", b"bytes", "audio/webm")}), 201)
    ok("admin prevalida (alertas)", c.post(f"/prescriptions/{rid}/prevalidate", headers=adm))

    # 6) Admin: genera QR.
    qr = ok("admin genera QR", c.post(f"/prescriptions/{rid}/generate-qr", headers=adm)).json()
    codigo = qr["codigo_verificacion"]

    # 7) Admin: farmacia (verifica y dispensa, superusuario).
    ok("admin verifica QR", c.post("/pharmacy/verify-qr", headers=adm, json={"codigo": codigo}))
    ok("admin dispensa", c.post(f"/pharmacy/recipes/{rid}/dispense", headers=adm, json={"codigo_verificacion": codigo, "observaciones": "Entregado"}))
    print("     receta ahora:", c.get(f"/prescriptions/{rid}", headers=adm).json()["estado"])

    # 8) Admin: base farmacológica (RAG).
    up = c.post("/pharmacological-documents", headers=adm,
                files={"file": (f"doc{suf}.txt", b"El enalapril es un antihipertensivo IECA.", "text/plain")},
                data={"titulo": "Doc demo", "fuente": "Guia", "version": "1"})
    did = up.json()["id_documento"]
    ok("admin procesa documento (embeddings)", c.post(f"/pharmacological-documents/{did}/process", headers=adm))
    ok("admin busca en RAG", c.post("/pharmacological-knowledge/search", headers=adm, json={"query": "enalapril antihipertensivo"}))

    # 9) Admin: chatbot del portal (sin registro propio -> respuesta general).
    chat_adm = c.post("/patient-portal/chat", headers=adm, json={"mensaje": "¿Cómo recojo una receta en farmacia?"})
    ok("admin usa chatbot", chat_adm)
    print("     respuesta:", chat_adm.json()["respuesta"][:90].replace(chr(10), " "), "...")

    print("\n== PACIENTE con la cuenta creada por el admin ==")
    pac = login(uname, "clave123")
    ok("paciente login + perfil", c.get("/patient-portal/profile", headers=pac))
    recs = c.get("/patient-portal/recipes", headers=pac).json()
    print("     mis recetas:", len(recs), "| estado:", recs[0]["estado"], "| dispensación:", recs[0]["estado_dispensacion"])
    chat = c.post("/patient-portal/chat", headers=pac, json={"mensaje": "¿Cuál es el estado de mi receta y mi medicamento?"})
    print("     chatbot:", chat.json()["respuesta"][:110].replace(chr(10), " "), "...")
    refuse = c.post("/patient-portal/chat", headers=pac, json={"mensaje": "Diagnostícame, ¿qué enfermedad tengo?"})
    print("     chatbot diagnóstico ->", refuse.json()["respuesta"])

    print("\nE2E FULL OK")


if __name__ == "__main__":
    main()
