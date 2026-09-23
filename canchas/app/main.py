import pika
import redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from contextlib import asynccontextmanager
import logging

from app.config import NOMBRE_APP, REDIS_URL, RABBITMQ_URL
from app.db import engine, Base
from app.datos import tablas  # noqa: F401  (registra las tablas en Base)
from app.rutas import rutas_canchas

log = logging.getLogger("canchas")


@asynccontextmanager
async def ciclo_de_vida(app):
    # Al arrancar, crea las tablas que no existan todavía.
    Base.metadata.create_all(engine)
    yield

# ===== PUNTO DE ENTRADA DEL SERVICIO DE CANCHAS =====

app = FastAPI(
    title=NOMBRE_APP,
    description="AE2 - Módulo de Canchas y Disponibilidad",
    version="2.0.0",
    lifespan=ciclo_de_vida,
)

app.include_router(rutas_canchas.router)


@app.exception_handler(Exception)
async def error_no_controlado(request, exc):
    # A diferencia del AE1, no se devuelve el detalle interno al cliente:
    # se registra en el log y se responde un mensaje genérico.
    log.exception("Error no controlado en %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


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
