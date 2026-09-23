import pika
import redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import NOMBRE_APP, REDIS_URL, RABBITMQ_URL
from app.db import engine

# ===== PUNTO DE ENTRADA DEL SERVICIO DE CANCHAS =====

app = FastAPI(
    title=NOMBRE_APP,
    description="AE2 - Módulo de Canchas y Disponibilidad",
    version="2.0.0",
)


@app.get("/health", tags=["Salud"])
def health():
    """Informa si el servicio y sus dependencias (DB, Redis, RabbitMQ) responden."""
    estado = {}

    try:
        with engine.connect() as conexion:
            conexion.execute(text("SELECT 1"))
        estado["base_de_datos"] = "ok"
    except Exception:
        estado["base_de_datos"] = "caida"

    try:
        redis.from_url(REDIS_URL, socket_timeout=2).ping()
        estado["redis"] = "ok"
    except Exception:
        estado["redis"] = "caido"

    try:
        parametros = pika.URLParameters(RABBITMQ_URL)
        parametros.socket_timeout = 2
        pika.BlockingConnection(parametros).close()
        estado["rabbitmq"] = "ok"
    except Exception:
        estado["rabbitmq"] = "caido"

    todo_ok = all(v == "ok" for v in estado.values())
    return JSONResponse(
        status_code=200 if todo_ok else 503,
        content={"estado": "ok" if todo_ok else "degradado", "dependencias": estado},
    )
