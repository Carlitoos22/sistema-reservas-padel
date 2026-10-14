# Desafío práctico U4: batería mínima de 3 tests (unitario, integración 201 y borde)
# Cada test sigue el patrón AAA: Arrange (preparar), Act (actuar), Assert (afirmar).
from datetime import time

import pytest

from app.controladores.controlador_disponibilidad import generar_turnos
from app.modelos.cancha import Cancha
from tests.test_canchas import CANCHA


# 1. TEST UNITARIO PURO
# Regla de negocio: los turnos se calculan con el horario de la cancha y la
# duración del turno. Un turno que no termina antes del cierre no se ofrece.
# Es una función pura: no usa base de datos, ni Redis, ni la red.
def test_unitario_turnos_que_no_entran_antes_del_cierre_no_se_ofrecen():
    # Arrange: cancha de 18:00 a 22:00 con turnos de 90 minutos
    apertura, cierre, duracion = time(18, 0), time(22, 0), 90

    # Act
    turnos = generar_turnos(apertura, cierre, duracion)

    # Assert: 18:00-19:30 y 19:30-21:00 entran; 21:00-22:30 se pasa del cierre
    assert turnos == [(time(18, 0), time(19, 30)), (time(19, 30), time(21, 0))]


# 2. TEST DE INTEGRACIÓN 201
# Petición HTTP real a la API (FastAPI + SQLAlchemy + base de datos) con un
# payload válido. Verifica el status 201 y que el JSON respete el contrato.
def test_integracion_crear_cancha_devuelve_201_y_schema_json(cliente):
    # Arrange: payload válido según el contrato OpenAPI
    payload = {**CANCHA, "nombre": "Cancha Central"}

    # Act
    respuesta = cliente.post("/api/v1/canchas", json=payload)

    # Assert: status 201 Created
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    # Assert: exactamente las claves pactadas en el contrato, ni una más ni una menos
    assert set(cuerpo) == {
        "id", "nombre", "tipo", "techada", "precio_turno",
        "hora_apertura", "hora_cierre", "duracion_turno_min", "activa",
    }
    # Assert: tipos y formatos correctos (el modelo Pydantic del contrato lo valida)
    Cancha.model_validate(cuerpo)
    assert isinstance(cuerpo["id"], int)
    assert cuerpo["nombre"] == "Cancha Central"
    assert cuerpo["activa"] is True


# 3. TEST DE BORDE (datos corruptos o en el límite)
# El sistema tiene que rechazar el pedido con un error del cliente (4xx) y
# nunca romperse con un 500. FastAPI responde 422 Unprocessable Entity, que es
# su código 4xx para datos inválidos (el equivalente al 400 Bad Request).
@pytest.mark.parametrize(
    "descripcion, cuerpo",
    [
        ("duración 29 min, justo debajo del mínimo de 30", {**CANCHA, "duracion_turno_min": 29}),
        ("precio 0, en el límite de lo permitido", {**CANCHA, "precio_turno": 0}),
        ("tipo de dato incorrecto en el precio", {**CANCHA, "precio_turno": "gratis"}),
        ("falta un campo obligatorio", {k: v for k, v in CANCHA.items() if k != "nombre"}),
        ("JSON corrupto, cortado a la mitad", '{"nombre": "Cancha 1", "tipo": "cris'),
    ],
    ids=["duracion_29", "precio_0", "precio_texto", "falta_nombre", "json_corrupto"],
)
def test_borde_datos_invalidos_se_rechazan_sin_error_500(cliente, descripcion, cuerpo):
    # Arrange: payload corrupto o en el límite (viene del parametrize)
    if isinstance(cuerpo, str):
        pedido = {"content": cuerpo, "headers": {"Content-Type": "application/json"}}
    else:
        pedido = {"json": cuerpo}

    # Act
    respuesta = cliente.post("/api/v1/canchas", **pedido)

    # Assert: rechazo del lado del cliente, nunca un error interno del servidor
    assert respuesta.status_code == 422, descripcion
    assert respuesta.status_code != 500
    # Assert: no se guardó nada
    assert cliente.get("/api/v1/canchas").json() == []


def test_borde_duracion_30_min_es_el_minimo_valido(cliente):
    # Arrange: el valor exacto del límite inferior
    payload = {**CANCHA, "duracion_turno_min": 30}

    # Act
    respuesta = cliente.post("/api/v1/canchas", json=payload)

    # Assert: 30 está permitido (29 no), así que la cancha se crea
    assert respuesta.status_code == 201
