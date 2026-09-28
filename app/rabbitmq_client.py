import pika
import json

# ===== CLIENTE RABBITMQ (PRODUCTOR) =====
# Publica mensajes en una cola para que un consumidor los procese aparte.

NOMBRE_COLA = "reservas_confirmadas"


def publicar_reserva_confirmada(reserva):
    """Publica un evento 'reserva_confirmada' en la cola de RabbitMQ."""
    try:
        # Conexión a RabbitMQ (corre en localhost, puerto 5672)
        conexion = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost", port=5672)
        )
        canal = conexion.channel()

        # Nos aseguramos de que la cola exista (durable = sobrevive reinicios)
        canal.queue_declare(queue=NOMBRE_COLA, durable=True)

        # Armamos el mensaje con los datos de la reserva
        mensaje = json.dumps({
            "id": reserva.id,
            "nombre_jugador": reserva.nombre_jugador,
            "cancha": reserva.cancha,
            "fecha": reserva.fecha,
            "hora": reserva.hora
        })

        # Publicamos el mensaje en la cola
        canal.basic_publish(
            exchange="",
            routing_key=NOMBRE_COLA,
            body=mensaje,
            properties=pika.BasicProperties(delivery_mode=2)  # mensaje persistente
        )

        conexion.close()
        print(f"[Productor] Evento publicado: reserva {reserva.id} confirmada")

    except Exception as e:
        # Si RabbitMQ no está disponible, no rompemos la reserva
        print(f"[Productor] No se pudo publicar el evento: {e}")