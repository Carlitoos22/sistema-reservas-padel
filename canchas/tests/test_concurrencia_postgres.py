# Caso de concurrencia (criterio 7): bloqueo y reserva de la misma franja al mismo tiempo.
#
# Corre contra PostgreSQL REAL (el de docker compose), porque el problema depende
# de cómo aísla las transacciones el motor: SQLite no permite reproducirlo.
# Usa un esquema propio ("prueba_concurrencia") que se borra al terminar, así no
# toca los datos de la base del servicio. Si no hay PostgreSQL, se saltea.
#
# La carrera (write skew):
#   T1 crea el bloqueo  -> lee ocupaciones de la franja: no ve la reserva
#   T2 aplica la reserva -> lee bloqueos de la franja:   no ve el bloqueo
#   T1 confirma: TurnoBloqueado con reservas_afectadas = []
#   T2 confirma: no emite ReservaEnConflicto
#   => la reserva choca con el bloqueo y NADIE se entera: el jugador llega a una
#      cancha cerrada.
#
# Para no depender de la suerte, las pruebas fuerzan ese intercalado: cada
# transacción, después de leer, espera (hasta 1 s) a que la otra también haya leído.
import json
import threading
import time
import uuid
from datetime import date, datetime, time as hora, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL
from app.db import Base
from app.datos import tablas, repositorio_bloqueos, repositorio_canchas, repositorio_ocupaciones
from app.controladores import controlador_bloqueos
from app.controladores.controlador_ocupacion import procesar_evento
from app.modelos.bloqueo import BloqueoEntrada
from app.modelos.evento import EventoReserva

ESQUEMA = "prueba_concurrencia"
FECHA = date.today() + timedelta(days=10)
ESPERA_MAX = 1.0


def _postgres_disponible():
    if not DATABASE_URL.startswith("postgresql"):
        return False
    try:
        with create_engine(DATABASE_URL).connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _postgres_disponible(), reason="requiere PostgreSQL (docker compose)")


@pytest.fixture
def Sesion(redis_falso):
    base = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    with base.connect() as c:
        c.execute(text(f"DROP SCHEMA IF EXISTS {ESQUEMA} CASCADE"))
        c.execute(text(f"CREATE SCHEMA {ESQUEMA}"))
    motor = create_engine(DATABASE_URL, connect_args={"options": f"-csearch_path={ESQUEMA}"})
    Base.metadata.create_all(motor)
    fabrica = sessionmaker(bind=motor)
    with fabrica() as s:
        s.add(tablas.CanchaTabla(nombre="Cancha 1", tipo="cristal", techada=False, precio_turno=15000,
                                 hora_apertura=hora(8), hora_cierre=hora(23, 30), duracion_turno_min=90, activa=True))
        s.commit()
    yield fabrica
    motor.dispose()
    with base.connect() as c:
        c.execute(text(f"DROP SCHEMA IF EXISTS {ESQUEMA} CASCADE"))
    base.dispose()


@pytest.fixture
def intercalado(monkeypatch):
    """Hace que cada transacción, después de LEER, espere a que la otra también lea."""
    leyo = {"bloqueo": threading.Event(), "reserva": threading.Event()}

    def esperar_a_la_otra(yo, otra):
        leyo[yo].set()
        leyo[otra].wait(ESPERA_MAX)

    original_ocupaciones = repositorio_ocupaciones.listar_activas
    original_bloqueos = repositorio_bloqueos.buscar_superpuestos

    def listar_activas(*a, **k):                     # lo usa la creación del bloqueo
        r = original_ocupaciones(*a, **k)
        if threading.current_thread().name == "bloqueo":
            esperar_a_la_otra("bloqueo", "reserva")
        return r

    def buscar_superpuestos(*a, **k):                # lo usa la aplicación de la reserva
        r = original_bloqueos(*a, **k)
        if threading.current_thread().name == "reserva":
            esperar_a_la_otra("reserva", "bloqueo")
        return r

    monkeypatch.setattr(repositorio_ocupaciones, "listar_activas", listar_activas)
    monkeypatch.setattr(repositorio_bloqueos, "buscar_superpuestos", buscar_superpuestos)


def correr_en_paralelo(Sesion, primero="bloqueo"):
    errores = []

    def crear_bloqueo():
        with Sesion() as s:
            controlador_bloqueos.crear_bloqueo(s, 1, BloqueoEntrada(
                fecha=FECHA, hora_desde=hora(14), hora_hasta=hora(18), motivo="Torneo"))

    def aplicar_reserva():
        with Sesion() as s:
            procesar_evento(s, EventoReserva.model_validate({
                "event_id": str(uuid.uuid4()), "tipo": "ReservaCreada",
                "ocurrido_en": datetime.now().isoformat(), "correlation_id": "reserva-50",
                "datos": {"reserva_id": 50, "cancha_id": 1, "fecha": FECHA.isoformat(),
                          "hora_inicio": "14:00", "hora_fin": "15:30"},
            }))

    def envolver(funcion):
        def correr():
            try:
                funcion()
            except Exception as e:  # noqa: BLE001
                errores.append(e)
        return correr

    hilos = {"bloqueo": threading.Thread(target=envolver(crear_bloqueo), name="bloqueo"),
             "reserva": threading.Thread(target=envolver(aplicar_reserva), name="reserva")}
    segundo = "reserva" if primero == "bloqueo" else "bloqueo"
    hilos[primero].start()
    time.sleep(0.2)                                  # que el primero tome el lock
    hilos[segundo].start()
    for h in hilos.values():
        h.join(10)
    assert not errores, errores


def veces_informada(Sesion):
    """Por cuántos caminos se informó que la reserva 50 choca con el bloqueo."""
    with Sesion() as s:
        filas = s.query(tablas.OutboxTabla).all()
    veces = 0
    for f in filas:
        datos = json.loads(f.cuerpo)["datos"]
        if f.tipo == "TurnoBloqueado" and 50 in datos["reservas_afectadas"]:
            veces += 1
        if f.tipo == "ReservaEnConflicto" and datos["reserva_id"] == 50:
            veces += 1
    return veces


def test_sin_lock_la_reserva_en_conflicto_se_pierde(Sesion, intercalado, monkeypatch):
    """Demuestra el problema: se quita el SELECT ... FOR UPDATE sobre la cancha."""
    monkeypatch.setattr(repositorio_canchas, "buscar_por_id_para_modificar", repositorio_canchas.buscar_por_id)
    correr_en_paralelo(Sesion)
    with Sesion() as s:
        assert s.query(tablas.BloqueoTabla).count() == 1       # el bloqueo quedó
        assert s.query(tablas.OcupacionTabla).count() == 1     # la reserva quedó
    assert veces_informada(Sesion) == 0                        # ...y nadie avisó del choque


@pytest.mark.parametrize("primero", ["bloqueo", "reserva"])
def test_con_lock_la_reserva_se_informa_una_sola_vez(Sesion, intercalado, primero):
    """Con el lock, gane quien gane, el choque se informa exactamente una vez:
    en reservas_afectadas si la reserva confirmó primero, o como
    ReservaEnConflicto si el bloqueo confirmó primero."""
    correr_en_paralelo(Sesion, primero)
    assert veces_informada(Sesion) == 1
    with Sesion() as s:
        tipos = {f.tipo for f in s.query(tablas.OutboxTabla).all()}
    esperado = "ReservaEnConflicto" if primero == "bloqueo" else "TurnoBloqueado"
    assert esperado in tipos
