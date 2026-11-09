import os
import pika
import json

# ===== CONSUMIDOR DE RABBITMQ =====
# Escucha la cola y procesa los eventos de reservas confirmadas
# de forma independiente al servidor (desacoplado).
NOMBRE_COLA = "reservas_confirmadas"
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")


def procesar_mensaje(ch, method, properties, body):
    """Se ejecuta cada vez que llega un mensaje a la cola."""
    reserva = json.loads(body)
    print("=" * 50)
    print(f"[*] Evento recibido: reserva {reserva['id']} confirmada")
    print(f"    Jugador: {reserva['nombre_jugador']}")
    print(f"    Cancha:  {reserva['cancha']}")
    print(f"    Fecha:   {reserva['fecha']} {reserva['hora']}")
    print("    -> Generando comprobante y registrando en el log...")
    print("    OK Procesado correctamente")
    print("=" * 50)
    # Confirmamos a RabbitMQ que procesamos el mensaje (ack)
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    parametros = pika.URLParameters(RABBITMQ_URL)
    conexion = pika.BlockingConnection(parametros)
    canal = conexion.channel()

    canal.queue_declare(queue=NOMBRE_COLA, durable=True)
    canal.basic_consume(queue=NOMBRE_COLA, on_message_callback=procesar_mensaje)

    print("[Consumidor] Esperando eventos de reservas. Ctrl+C para salir.")
    canal.start_consuming()


if __name__ == "__main__":
    main()