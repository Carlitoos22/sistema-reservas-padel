import logging
import time

import pika
from pydantic import ValidationError

from app.config import RABBITMQ_URL
from app.db import SesionLocal, engine, Base
from app.datos import tablas  # noqa: F401  (registra las tablas en Base)
from app.mensajeria import declarar_topologia, COLA, MAX_REINTENTOS
from app.modelos.evento import EventoReserva
from app.controladores.controlador_ocupacion import procesar_evento, EventoInvalido

# ===== CONSUMIDOR DE EVENTOS DE RESERVAS =====
# Proceso separado de la API (otro contenedor): si la API se reinicia,
# los eventos quedan esperando en la cola, y viceversa.
#
# Qué pasa con cada mensaje:
#   - Se aplica bien, o es un duplicado      -> ack (sale de la cola)
#   - Mal formado o no aplicable             -> reject sin reencolar -> cola de fallidos
#   - Error transitorio (p. ej. base caída)  -> se republica con x-reintentos + 1;
#                                               al superar MAX_REINTENTOS -> cola de fallidos
# El ack se envía DESPUÉS de hacer commit. Si el consumidor se cae en el medio,
# RabbitMQ vuelve a entregar el mensaje y la idempotencia evita el doble efecto.

log = logging.getLogger("canchas.consumidor")


def manejar_mensaje(canal, metodo, propiedades, cuerpo, abrir_sesion=SesionLocal):
    reintentos = int((propiedades.headers or {}).get("x-reintentos", 0))

    try:
        evento = EventoReserva.model_validate_json(cuerpo)
    except ValidationError as error:
        log.error("Mensaje inválido, va a la cola de fallidos: %s", error.errors()[:1])
        canal.basic_reject(metodo.delivery_tag, requeue=False)
        return

    sesion = abrir_sesion()
    try:
        procesar_evento(sesion, evento)
        canal.basic_ack(metodo.delivery_tag)
    except EventoInvalido as error:
        log.error("Evento %s no aplicable (%s), va a la cola de fallidos", evento.event_id, error)
        canal.basic_reject(metodo.delivery_tag, requeue=False)
    except Exception:
        sesion.rollback()
        if reintentos >= MAX_REINTENTOS:
            log.exception("Evento %s falló %s veces, va a la cola de fallidos", evento.event_id, reintentos + 1)
            canal.basic_reject(metodo.delivery_tag, requeue=False)
            return
        log.warning("Error procesando %s, reintento %s de %s", evento.event_id, reintentos + 1, MAX_REINTENTOS)
        time.sleep(reintentos + 1)  # espera creciente: 1 s, 2 s, 3 s
        # Se republica directo a NUESTRA cola (exchange por defecto), no al exchange
        # "reservas": así el reintento no les llega duplicado a otros servicios.
        canal.basic_publish(
            exchange="",
            routing_key=COLA,
            body=cuerpo,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                headers={"x-reintentos": reintentos + 1},
            ),
        )
        canal.basic_ack(metodo.delivery_tag)
    finally:
        sesion.close()


def conectar(intentos=10):
    """RabbitMQ puede tardar en aceptar conexiones aunque el healthcheck ya pase."""
    for intento in range(1, intentos + 1):
        try:
            return pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        except (pika.exceptions.AMQPConnectionError, OSError):  # OSError: p. ej. socket.gaierror
            log.warning("RabbitMQ no disponible (intento %s de %s)", intento, intentos)
            time.sleep(3)
    raise RuntimeError("No se pudo conectar a RabbitMQ")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("pika").setLevel(logging.WARNING)  # los logs de conexión tapaban los del negocio
    Base.metadata.create_all(engine)
    conexion = conectar()
    canal = conexion.channel()
    declarar_topologia(canal)
    canal.basic_qos(prefetch_count=1)  # de a un mensaje: no se toma el siguiente hasta confirmar
    canal.basic_consume(COLA, manejar_mensaje)
    log.info("Consumidor escuchando la cola %s", COLA)
    canal.start_consuming()


if __name__ == "__main__":
    main()
