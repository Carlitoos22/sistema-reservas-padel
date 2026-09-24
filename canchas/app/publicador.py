import logging
import time
from datetime import datetime

import pika

from app.config import RABBITMQ_URL
from app.db import SesionLocal, engine, Base
from app.datos import tablas  # noqa: F401  (registra las tablas en Base)
from app.datos import repositorio_outbox
from app.mensajeria import declarar_exchange_canchas, EXCHANGE_CANCHAS

# ===== PUBLICADOR DEL OUTBOX =====
# Proceso separado (contenedor canchas-publicador). Cada INTERVALO segundos:
#   1. toma los eventos pendientes del outbox,
#   2. los publica en el exchange "canchas" y espera la confirmación del broker
#      (publisher confirms): recién ahí RabbitMQ garantiza que lo guardó,
#   3. los marca como publicados.
# Si el broker no responde, no se marca nada: el próximo ciclo reintenta.
# Si se cae justo entre 2 y 3, el evento se publica otra vez al volver
# (entrega "al menos una vez"); por eso cada evento lleva event_id y el
# consumidor debe ser idempotente, igual que el nuestro en la etapa 7.

log = logging.getLogger("canchas.publicador")
INTERVALO = 2


def publicar_pendientes(canal, abrir_sesion=SesionLocal) -> int:
    sesion = abrir_sesion()
    publicados = 0
    try:
        for fila in repositorio_outbox.tomar_pendientes(sesion):
            fila.intentos += 1
            canal.basic_publish(
                exchange=EXCHANGE_CANCHAS,
                routing_key=fila.routing_key,
                body=fila.cuerpo,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                    message_id=fila.event_id,
                ),
            )
            fila.publicado_en = datetime.now()
            publicados += 1
            log.info("Publicado %s %s", fila.tipo, fila.event_id)
        sesion.commit()
    except Exception:
        # Se guardan igual los que sí se confirmaron antes del error.
        sesion.commit()
        raise
    finally:
        sesion.close()
    return publicados


def conectar():
    conexion = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    canal = conexion.channel()
    canal.confirm_delivery()  # basic_publish espera el ack del broker
    declarar_exchange_canchas(canal)
    return conexion, canal


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("pika").setLevel(logging.WARNING)
    Base.metadata.create_all(engine)
    conexion = canal = None
    log.info("Publicador del outbox iniciado (cada %s s)", INTERVALO)
    while True:
        try:
            if conexion is None or conexion.is_closed:
                conexion, canal = conectar()
                log.info("Conectado a RabbitMQ")
            publicar_pendientes(canal)
            conexion.process_data_events(time_limit=0)  # mantiene vivo el heartbeat
        # OSError cubre fallas de red que pika no envuelve en sus propias
        # excepciones, como socket.gaierror cuando el host "rabbitmq" no
        # resuelve porque el contenedor está detenido.
        except (pika.exceptions.AMQPError, OSError) as error:
            log.warning("RabbitMQ no disponible (%s); los eventos quedan en el outbox", type(error).__name__)
            conexion = None
        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
