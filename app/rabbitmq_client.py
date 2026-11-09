import os
import pika
import json

# ===== CLIENTE RABBITMQ (PRODUCTOR) =====
# Publica mensajes en una cola para que un consumidor los procese aparte.
NOMBRE_COLA = "reservas_confirmadas"
# En local usa guest@localhost:5672; en la nube usa la variable RABBITMQ_URL.
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")


def publicar_reserva_confirmada(reserva):
    """Publica un evento 'reserva_confirmada' en la cola de RabbitMQ."""
    try:
        parametros = pika.URLParameters(RABBITMQ_URL)
        conexion = pika.BlockingConnection(parametros)
        canal = conexion.channel()

        # Nos aseguramos de que la cola exista (durable = sobrevive reinicios)
        canal.queue_declare(queue=NOMBRE_COLA, durable=True)

        mensaje = json.dumps({
            "id": reserva.id,
            "nombre_jugador": reserva.nombre_jugador,
            "cancha": reserva.cancha,
            "fecha": reserva.fecha,
            "hora": reserva.hora,
        })

        canal.basic_publish(
            exchange="",
            routing_key=NOMBRE_COLA,
            body=mensaje,
            properties=pika.BasicProperties(delivery_mode=2),  # mensaje persistente
        )

        conexion.close()
        print(f"[Productor] Evento publicado: reserva {reserva.id} confirmada")
    except Exception as e:
        # Si RabbitMQ no esta disponible, no rompemos la reserva
        print(f"[Productor] No se pudo publicar el evento: {e}")