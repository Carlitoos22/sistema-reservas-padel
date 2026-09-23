# Pruebas de consulta de disponibilidad (RF-C2)
from datetime import date, time, timedelta
from app.controladores.controlador_disponibilidad import generar_turnos
from tests.test_canchas import CANCHA

FECHA = str(date.today() + timedelta(days=7))


# --- Pruebas unitarias del cálculo de turnos (sin base de datos) ---

def test_generar_turnos_de_90_minutos():
    turnos = generar_turnos(time(8, 0), time(23, 30), 90)
    assert len(turnos) == 10
    assert turnos[0] == (time(8, 0), time(9, 30))
    assert turnos[-1] == (time(21, 30), time(23, 0))  # 23:00-00:30 no entra


def test_generar_turnos_exactos_hasta_el_cierre():
    turnos = generar_turnos(time(10, 0), time(14, 0), 60)
    assert len(turnos) == 4
    assert turnos[-1] == (time(13, 0), time(14, 0))


def test_generar_turnos_cuando_no_entra_ninguno():
    assert generar_turnos(time(10, 0), time(10, 30), 60) == []


# --- Pruebas del endpoint ---

def disponibilidad(cliente, id_cancha=1, fecha=FECHA):
    return cliente.get(f"/api/v1/canchas/{id_cancha}/disponibilidad?fecha={fecha}")


def test_cancha_sin_bloqueos_todo_libre(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    r = disponibilidad(cliente)
    assert r.status_code == 200
    turnos = r.json()["turnos"]
    assert len(turnos) == 10
    assert all(t["estado"] == "libre" for t in turnos)


def test_bloqueo_marca_los_turnos_que_toca(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    # Bloqueo de 14:00 a 18:00:
    #   12:30-14:00 libre      (termina justo cuando empieza el bloqueo)
    #   14:00-15:30 bloqueado
    #   15:30-17:00 bloqueado
    #   17:00-18:30 bloqueado  (se superpone en parte: no se puede ofrecer)
    #   18:30-20:00 libre
    cliente.post("/api/v1/canchas/1/bloqueos",
                 json={"fecha": FECHA, "hora_desde": "14:00", "hora_hasta": "18:00", "motivo": "Torneo"})
    turnos = {t["hora_inicio"][:5]: t["estado"] for t in disponibilidad(cliente).json()["turnos"]}
    assert turnos["12:30"] == "libre"
    assert turnos["14:00"] == "bloqueado"
    assert turnos["15:30"] == "bloqueado"
    assert turnos["17:00"] == "bloqueado"
    assert turnos["18:30"] == "libre"


def test_bloqueo_de_otro_dia_no_afecta(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    otro_dia = str(date.today() + timedelta(days=8))
    cliente.post("/api/v1/canchas/1/bloqueos",
                 json={"fecha": otro_dia, "hora_desde": "08:00", "hora_hasta": "23:30", "motivo": "Torneo"})
    assert all(t["estado"] == "libre" for t in disponibilidad(cliente).json()["turnos"])


def test_cancha_inexistente_da_404(cliente):
    assert disponibilidad(cliente, id_cancha=99).status_code == 404


def test_cancha_inactiva_da_409(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    cliente.delete("/api/v1/canchas/1")
    assert disponibilidad(cliente).status_code == 409


def test_fecha_pasada_da_422(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    ayer = str(date.today() - timedelta(days=1))
    assert disponibilidad(cliente, fecha=ayer).status_code == 422


def test_sin_fecha_da_422(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    assert cliente.get("/api/v1/canchas/1/disponibilidad").status_code == 422
