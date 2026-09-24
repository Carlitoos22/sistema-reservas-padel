# Pruebas de la publicación de TurnoBloqueado mediante outbox
import json
import uuid
from datetime import datetime

import pika
import pytest

from app.controladores.controlador_ocupacion import procesar_evento
from app.datos.tablas import OutboxTabla
from app.modelos.evento import EventoReserva
from app.publicador import publicar_pendientes
from tests.test_bloqueos import FECHA, bloquear, crear_cancha


def filas_outbox(sesion):
    sesion.expire_all()
    return sesion.query(OutboxTabla).order_by(OutboxTabla.id).all()


def reservar(sesion, reserva_id, hora, fin, tipo="ReservaCreada"):
    procesar_evento(sesion, EventoReserva.model_validate({
        "event_id": str(uuid.uuid4()), "tipo": tipo, "ocurrido_en": datetime.now().isoformat(),
        "correlation_id": f"reserva-{reserva_id}",
        "datos": {"reserva_id": reserva_id, "cancha_id": 1, "fecha": FECHA,
                  "hora_inicio": hora, "hora_fin": fin},
    }))


# --- El evento se guarda junto con el bloqueo ---

def test_crear_bloqueo_deja_el_evento_en_el_outbox(cliente, sesion):
    crear_cancha(cliente)
    r = bloquear(cliente)  # 14:00 a 18:00
    filas = filas_outbox(sesion)
    assert len(filas) == 1
    fila = filas[0]
    assert fila.tipo == "TurnoBloqueado" and fila.routing_key == "turno.bloqueado"
    assert fila.publicado_en is None
    datos = json.loads(fila.cuerpo)["datos"]
    assert datos["bloqueo_id"] == r.json()["id"]
    assert (datos["fecha"], datos["hora_desde"], datos["hora_hasta"]) == (FECHA, "14:00:00", "18:00:00")


def test_bloqueo_rechazado_no_genera_evento(cliente, sesion):
    """Atomicidad: si el bloqueo no se guarda, tampoco su evento."""
    crear_cancha(cliente)
    bloquear(cliente)
    assert bloquear(cliente, hora_desde="15:00", hora_hasta="16:00").status_code == 409
    assert len(filas_outbox(sesion)) == 1


def test_el_evento_informa_las_reservas_afectadas(cliente, sesion):
    crear_cancha(cliente)
    reservar(sesion, 20, "12:30", "14:00")   # termina justo cuando empieza el bloqueo: no afectada
    reservar(sesion, 21, "14:00", "15:30")   # dentro del bloqueo
    reservar(sesion, 22, "17:00", "18:30")   # se superpone con el final
    reservar(sesion, 23, "15:30", "17:00")
    reservar(sesion, 23, "15:30", "17:00", tipo="ReservaCancelada")  # cancelada: no afectada
    bloquear(cliente)
    datos = json.loads(filas_outbox(sesion)[0].cuerpo)["datos"]
    assert datos["reservas_afectadas"] == [21, 22]


# --- El publicador ---

class CanalFalso:
    def __init__(self, fallar_en=None):
        self.publicados, self.fallar_en = [], fallar_en

    def basic_publish(self, exchange, routing_key, body, properties):
        if self.fallar_en is not None and len(self.publicados) == self.fallar_en:
            raise pika.exceptions.AMQPConnectionError("broker caído")
        self.publicados.append((exchange, routing_key, json.loads(body)["event_id"], properties.message_id))


def fabrica(sesion):
    sesion.close = lambda: None
    return lambda: sesion


def test_publicador_envia_y_marca_publicado(cliente, sesion):
    crear_cancha(cliente)
    bloquear(cliente)
    canal = CanalFalso()
    assert publicar_pendientes(canal, fabrica(sesion)) == 1
    event_id = filas_outbox(sesion)[0].event_id
    assert canal.publicados == [("canchas", "turno.bloqueado", event_id, event_id)]
    assert filas_outbox(sesion)[0].publicado_en is not None
    assert publicar_pendientes(canal, fabrica(sesion)) == 0  # no se publica dos veces


def test_broker_caido_el_evento_queda_pendiente(cliente, sesion):
    crear_cancha(cliente)
    assert bloquear(cliente).status_code == 201  # el bloqueo no depende de RabbitMQ
    with pytest.raises(pika.exceptions.AMQPError):
        publicar_pendientes(CanalFalso(fallar_en=0), fabrica(sesion))
    fila = filas_outbox(sesion)[0]
    assert fila.publicado_en is None and fila.intentos == 1
    assert publicar_pendientes(CanalFalso(), fabrica(sesion)) == 1  # cuando vuelve, sale


def test_falla_a_mitad_conserva_los_ya_publicados(cliente, sesion):
    crear_cancha(cliente)
    bloquear(cliente, hora_desde="09:00", hora_hasta="10:00")
    bloquear(cliente, hora_desde="14:00", hora_hasta="18:00")
    with pytest.raises(pika.exceptions.AMQPError):
        publicar_pendientes(CanalFalso(fallar_en=1), fabrica(sesion))
    primera, segunda = filas_outbox(sesion)
    assert primera.publicado_en is not None
    assert segunda.publicado_en is None


def test_publicador_sobrevive_si_rabbitmq_no_resuelve(monkeypatch):
    """Bug detectado en la prueba real: con el contenedor de RabbitMQ detenido,
    pika deja pasar socket.gaierror (no es una excepción de pika) y el
    publicador se caía. Ahora lo registra como aviso y sigue intentando."""
    import socket
    from app import publicador

    def conectar_falla():
        raise socket.gaierror(-2, "Name or service not known")

    ciclos = []

    def dormir(segundos):
        ciclos.append(segundos)
        if len(ciclos) == 2:
            raise SystemExit  # corta el bucle infinito después de dos ciclos

    monkeypatch.setattr(publicador, "conectar", conectar_falla)
    monkeypatch.setattr(publicador.time, "sleep", dormir)
    monkeypatch.setattr(publicador.Base.metadata, "create_all", lambda engine: None)
    with pytest.raises(SystemExit):
        publicador.main()
    assert len(ciclos) == 2  # no se cayó en el primer intento: siguió reintentando
