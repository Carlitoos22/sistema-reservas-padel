import requests

BASE = "http://127.0.0.1:8000"
URL = f"{BASE}/api/v1/reservas"

print("=== Consigna 2: Sanitizacion / Error 400 ===\n")

payloads_maliciosos = [
    {"nombre_jugador": "<script>alert('x')</script>", "cancha": "Cancha 1",
    "fecha": "2026-11-01", "hora": "18:00"},
    {"nombre_jugador": "Robert'); DROP TABLE reservas;--", "cancha": "Cancha 1",
    "fecha": "2026-11-01", "hora": "19:00"},
    {"nombre_jugador": "Carlos", "cancha": "Cancha <1>",
    "fecha": "2026-11-01", "hora": "20:00"},
]

hubo_500 = False
for i, p in enumerate(payloads_maliciosos, 1):
    try:
        r = requests.post(URL, json=p, timeout=10)
        if r.status_code == 400:
            marca = "OK (rechazado limpio)"
        elif r.status_code == 500:
            marca = "MAL -> 500 (el servidor crasheo!)"
            hubo_500 = True
        else:
            marca = "revisar (esperaba 400)"
        print(f"Payload {i}: HTTP {r.status_code}  -> {marca}")
    except Exception as e:
        print(f"Payload {i}: no se pudo conectar ({e})")

print("\nEsperado: los 3 en 400. NINGUNO en 500.")
print("Resultado:", "NO hubo 500 (bien)" if not hubo_500 else "HUBO 500 (falta aplicar la validacion)")

print("\n=== Consigna 3: Headers de seguridad ===\n")
try:
    r = requests.get(f"{BASE}/", timeout=10)
    for h in ["X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy", "Referrer-Policy"]:
        valor = r.headers.get(h)
        print(f"{h:<26}: {valor if valor else 'FALTA'}")
except Exception as e:
    print(f"No se pudo conectar: {e}")