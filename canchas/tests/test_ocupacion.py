# Pruebas de la ocupación por eventos de Reservas (RF-C5) e idempotencia
import uuid
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError

from app.consumidor import manejar_mensaje
from app.controladores.controlador_ocupacion import procesar_evento, PROCESADO, DUPLICADO, EventoInvalido
from app.modelos.evento import EventoReserva
from tests.test_canchas import CANCHA

FECHA = str(date.today() + timedelta(days=7))
URL = f"/api/v1/canchas/1/disponibilidad?fecha={FECHA}"


def evento(tipo="ReservaCreada", reserva=10, cancha=1, hora="09:30", fin="11:00", event_id=None):
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "tipo": tipo,
        "ocurrido_en": datetime.now().isoformat(),
        "correlation_id": f"reserva-{reserva}",
        "datos": {"reserva_id": reserva, "cancha_id": cancha, "fecha": FECHA,
                  "hora_inicio": hora, "hora_fin": fin},
    }


def aplicar(sesion, datos):
    return procesar_evento(sesion, EventoReserva.model_validate(datos))


def estado(cliente, hora="09:30"):
    turnos = cliente.get(URL).json()["turnos"]
    return next(t["estado"] for t in turnos if t["hora_inicio"].startswith(hora))


# --- Efecto sobre la disponibilidad ---

def test_reserva_creada_marca_el_turno_ocupado(cliente, sesion):
    cliente.post("/api/v1/canchas", json=CANCHA)
    assert aplicar(sesion, evento()) == PROCESADO
    assert estado(cliente) == "ocupado"
    assert estado(cliente, "08:00") == "libre"


def test_reserva_cancelada_libera_el_turno(cliente, sesion):
    cliente.post("/api/v1/canchas", json=CANCHA)
    aplicar(sesion, evento())
    aplicar(sesion, evento("ReservaCancelada"))
    assert estado(cliente) == "libre"


def test_el_evento_invalida_la_cache(cliente, sesion):
    cliente.post("/api/v1/canchas", json=CANCHA)
    cliente.get(URL)  # queda cacheado con el turno libre
    aplicar(sesion, evento())
    r = cliente.get(URL)
    assert r.headers["X-Cache"] == "MISS"
    assert estado(cliente) == "ocupado"


# --- Idempotencia y orden ---

def test_evento_duplicado_no_tiene_efecto(cliente, sesion):
    cliente.post("/api/v1/canchas", json=CANCHA)
    creada = evento()
    assert aplicar(sesion, creada) == PROCESADO
    assert aplicar(sesion, creada) == DUPLICADO


def test_cancelacion_duplicada_no_libera_una_reserva_nueva(cliente, sesion):
    """Caso realista: se cancela la reserva 10, otro jugador reserva ese turno (reserva 11)
    y recién ahí RabbitMQ reentrega la cancelación de la 10. El turno debe seguir ocupado."""
    cliente.post("/api/v1/canchas", json=CANCHA)
    cancelacion = evento("ReservaCancelada", reserva=10)
    aplicar(sesion, evento(reserva=10))
    aplicar(sesion, cancelacion)
    aplicar(sesion, evento(reserva=11))
    assert aplicar(sesion, cancelacion) == DUPLICADO
    assert estado(cliente) == "ocupado"


def test_cancelacion_antes_que_creacion(cliente, sesion):
    """Si los eventos llegan desordenados, la reserva cancelada no vuelve a quedar activa."""
    cliente.post("/api/v1/canchas", json=CANCHA)
    aplicar(sesion, evento("ReservaCancelada"))
    aplicar(sesion, evento("ReservaCreada"))
    assert estado(cliente) == "libre"


def test_cancha_inexistente_no_se_aplica(cliente, sesion):
    with pytest.raises(EventoInvalido):
        aplicar(sesion, evento(cancha=99))


# --- Comportamiento del consumidor ante cada tipo de mensaje ---

class CanalFalso:
    def __init__(self):
        self.acks, self.rechazos, self.publicados = [], [], []

    def basic_ack(self, tag): self.acks.append(tag)
    def basic_reject(self, tag, requeue): self.rechazos.append((tag, requeue))
    def basic_publish(self, exchange, routing_key, body, properties):
        self.publicados.append(properties.headers)


METODO = SimpleNamespace(delivery_tag=1, routing_key="reserva.creada")


def consumir(cuerpo, abrir_sesion, headers=None):
    canal = CanalFalso()
    manejar_mensaje(canal, METODO, SimpleNamespace(headers=headers), cuerpo, abrir_sesion)
    return canal


def fabrica(sesion):
    sesion.close = lambda: None  # la fixture la cierra al final
    return lambda: sesion


def test_consumidor_confirma_evento_valido(cliente, sesion):
    import json
    cliente.post("/api/v1/canchas", json=CANCHA)
    canal = consumir(json.dumps(evento()), fabrica(sesion))
    assert canal.acks == [1] and canal.rechazos == []


def test_mensaje_mal_formado_va_a_fallidos_sin_reintentar(sesion):
    canal = consumir(b'{"tipo": "ReservaCreada", "datos": "roto"}', fabrica(sesion))
    assert canal.rechazos == [(1, False)] and canal.publicados == []


def test_cancha_inexistente_va_a_fallidos(cliente, sesion):
    import json
    canal = consumir(json.dumps(evento(cancha=99)), fabrica(sesion))
    assert canal.rechazos == [(1, False)]


class SesionCaida:
    def get(self, *a, **k): raise OperationalError("SELECT", {}, Exception("base caída"))
    def rollback(self): pass
    def close(self): pass


def test_error_transitorio_se_reintenta(monkeypatch):
    import json
    monkeypatch.setattr("app.consumidor.time.sleep", lambda s: None)
    canal = consumir(json.dumps(evento()), lambda: SesionCaida())
    assert canal.publicados == [{"x-reintentos": 1}]
    assert canal.acks == [1]  # el original sale de la cola; queda la copia


def test_superados_los_reintentos_va_a_fallidos(monkeypatch):
    import json
    monkeypatch.setattr("app.consumidor.time.sleep", lambda s: None)
    canal = consumir(json.dumps(evento()), lambda: SesionCaida(), headers={"x-reintentos": 3})
    assert canal.rechazos == [(1, False)] and canal.publicados == []
