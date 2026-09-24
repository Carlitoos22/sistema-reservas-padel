"""Simula al módulo de Reservas escuchando los eventos que publica Canchas.

Uso (dentro del contenedor):
  python -m scripts.escuchar_eventos

Crea la cola "simulador.reservas" (durable) enganchada al exchange "canchas".
Como es durable, los eventos publicados mientras el script no corre quedan
esperando y se muestran la próxima vez. Ctrl+C para salir.
"""
import json
import pika

from app.config import RABBITMQ_URL
from app.mensajeria import declarar_exchange_canchas, EXCHANGE_CANCHAS

COLA = "simulador.reservas"


def mostrar(canal, metodo, propiedades, cuerpo):
    evento = json.loads(cuerpo)
    print(f"\n[{metodo.routing_key}] {evento['tipo']}  event_id={evento['event_id']}")
    print(json.dumps(evento["datos"], indent=2, ensure_ascii=False), flush=True)
    canal.basic_ack(metodo.delivery_tag)


def main():
    conexion = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    canal = conexion.channel()
    declarar_exchange_canchas(canal)
    canal.queue_declare(COLA, durable=True)
    canal.queue_bind(COLA, EXCHANGE_CANCHAS, routing_key="turno.*")
    canal.basic_consume(COLA, mostrar)
    print(f"Escuchando eventos de Canchas en la cola {COLA}... (Ctrl+C para salir)", flush=True)
    try:
        canal.start_consuming()
    except KeyboardInterrupt:
        conexion.close()


if __name__ == "__main__":
    main()
