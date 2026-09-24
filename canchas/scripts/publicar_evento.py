"""Simula al módulo de Reservas publicando un evento en RabbitMQ.

Uso (dentro del contenedor):
  python -m scripts.publicar_evento creada   --reserva 10 --cancha 1 --fecha 2026-10-01 --hora 09:30
  python -m scripts.publicar_evento cancelada --reserva 10 --cancha 1 --fecha 2026-10-01 --hora 09:30
  ... --repetir 2         publica el MISMO evento dos veces (prueba de idempotencia)
  python -m scripts.publicar_evento invalido                  mensaje mal formado (va a fallidos)
"""
import argparse
import json
import uuid
from datetime import datetime, date, time, timedelta

import pika

from app.config import RABBITMQ_URL
from app.mensajeria import declarar_topologia, EXCHANGE, CLAVES

TIPOS = {"creada": "ReservaCreada", "cancelada": "ReservaCancelada"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tipo", choices=["creada", "cancelada", "invalido"])
    p.add_argument("--reserva", type=int, default=1)
    p.add_argument("--cancha", type=int, default=1)
    p.add_argument("--fecha", default=str(date.today() + timedelta(days=7)))
    p.add_argument("--hora", default="09:30")
    p.add_argument("--duracion", type=int, default=90, help="minutos del turno")
    p.add_argument("--repetir", type=int, default=1)
    a = p.parse_args()

    if a.tipo == "invalido":
        tipo, cuerpo = "ReservaCreada", json.dumps({"tipo": "ReservaCreada", "datos": "roto"})
    else:
        tipo = TIPOS[a.tipo]
        inicio = time.fromisoformat(a.hora)
        fin = (datetime.combine(date.today(), inicio) + timedelta(minutes=a.duracion)).time()
        cuerpo = json.dumps({
            "event_id": str(uuid.uuid4()),
            "tipo": tipo,
            "ocurrido_en": datetime.now().isoformat(),
            "correlation_id": f"reserva-{a.reserva}",
            "datos": {"reserva_id": a.reserva, "cancha_id": a.cancha, "fecha": a.fecha,
                      "hora_inicio": inicio.isoformat(), "hora_fin": fin.isoformat()},
        })

    conexion = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    canal = conexion.channel()
    declarar_topologia(canal)
    for _ in range(a.repetir):
        canal.basic_publish(EXCHANGE, CLAVES[tipo], cuerpo,
                            pika.BasicProperties(delivery_mode=2, content_type="application/json"))
    conexion.close()
    print(f"Publicado {a.repetir}x: {cuerpo}")


if __name__ == "__main__":
    main()
