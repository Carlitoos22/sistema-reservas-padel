import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import requests

URL = "http://127.0.0.1:8000/api/v1/reservas"
CANTIDAD = 20


def una_peticion(_):
    inicio = time.perf_counter()
    try:
        r = requests.get(URL, timeout=10)
        ok = (r.status_code == 200)
        codigo = r.status_code
    except Exception as e:
        ok, codigo = False, f"ERROR({e})"
    duracion_ms = (time.perf_counter() - inicio) * 1000
    return ok, codigo, duracion_ms


if __name__ == "__main__":
    print(f"Disparando {CANTIDAD} peticiones concurrentes a:\n  {URL}\n")
    inicio_total = time.perf_counter()
    with ThreadPoolExecutor(max_workers=CANTIDAD) as pool:
        resultados = list(pool.map(una_peticion, range(CANTIDAD)))
    tiempo_total_ms = (time.perf_counter() - inicio_total) * 1000

    exitos = sum(1 for ok, _, _ in resultados if ok)
    latencias = [d for _, _, d in resultados]

    print("Codigos de respuesta:", [c for _, c, _ in resultados])
    print("-" * 42)
    print(f"Peticiones totales : {CANTIDAD}")
    print(f"Exitosas (200)     : {exitos}")
    print(f"Fallidas           : {CANTIDAD - exitos}")
    print(f"Tasa de exito      : {exitos / CANTIDAD * 100:.1f} %")
    print(f"Latencia media     : {statistics.mean(latencias):.1f} ms")
    print(f"Latencia min / max : {min(latencias):.1f} / {max(latencias):.1f} ms")
    print(f"Tiempo total       : {tiempo_total_ms:.1f} ms")