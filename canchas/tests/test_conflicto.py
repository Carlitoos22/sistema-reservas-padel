# Reserva que llega para una franja ya bloqueada -> ReservaEnConflicto
import json

from app.datos.tablas import OutboxTabla
from tests.test_bloqueos import bloquear, crear_cancha
from tests.test_outbox import reservar


def eventos(sesion, tipo):
    sesion.expire_all()
    return [json.loads(f.cuerpo) for f in sesion.query(OutboxTabla).filter_by(tipo=tipo)]


def test_reserva_sobre_franja_bloqueada_genera_conflicto(cliente, sesion):
    crear_cancha(cliente)
    bloqueo_id = bloquear(cliente).json()["id"]      # 14:00 a 18:00
    reservar(sesion, 30, "14:00", "15:30")           # llega después del bloqueo
    [conflicto] = eventos(sesion, "ReservaEnConflicto")
    assert conflicto["datos"]["reserva_id"] == 30
    assert [b["bloqueo_id"] for b in conflicto["datos"]["bloqueos"]] == [bloqueo_id]
    assert conflicto["correlation_id"] == "reserva-30"


def test_reserva_fuera_del_bloqueo_no_genera_conflicto(cliente, sesion):
    crear_cancha(cliente)
    bloquear(cliente)                                # 14:00 a 18:00
    reservar(sesion, 31, "12:30", "14:00")           # termina justo cuando empieza
    assert eventos(sesion, "ReservaEnConflicto") == []


def test_la_reserva_en_conflicto_igual_se_registra(cliente, sesion):
    """La reserva existe en Reservas: se guarda, y la disponibilidad muestra bloqueado."""
    from tests.test_bloqueos import FECHA
    crear_cancha(cliente)
    bloquear(cliente)
    reservar(sesion, 32, "14:00", "15:30")
    turnos = cliente.get(f"/api/v1/canchas/1/disponibilidad?fecha={FECHA}").json()["turnos"]
    assert next(t for t in turnos if t["hora_inicio"] == "14:00:00")["estado"] == "bloqueado"


def test_evento_duplicado_no_repite_el_conflicto(cliente, sesion):
    import uuid
    from datetime import datetime
    from app.controladores.controlador_ocupacion import procesar_evento
    from app.modelos.evento import EventoReserva
    from tests.test_bloqueos import FECHA
    crear_cancha(cliente)
    bloquear(cliente)
    evento = EventoReserva.model_validate({
        "event_id": str(uuid.uuid4()), "tipo": "ReservaCreada", "ocurrido_en": datetime.now().isoformat(),
        "correlation_id": "reserva-33",
        "datos": {"reserva_id": 33, "cancha_id": 1, "fecha": FECHA, "hora_inicio": "14:00", "hora_fin": "15:30"},
    })
    procesar_evento(sesion, evento)
    procesar_evento(sesion, evento)
    assert len(eventos(sesion, "ReservaEnConflicto")) == 1
