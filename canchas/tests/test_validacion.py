# Pruebas del endpoint de validación de turno que consume Reservas (RF-C4)
from datetime import date, timedelta
from tests.test_canchas import CANCHA

FECHA = str(date.today() + timedelta(days=7))


def validar(cliente, id_cancha=1, fecha=FECHA, hora="09:30"):
    return cliente.get(f"/api/v1/canchas/{id_cancha}/turnos/validar?fecha={fecha}&hora_inicio={hora}")


def test_turno_valido_devuelve_fin_y_precio(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    r = validar(cliente)
    assert r.status_code == 200
    datos = r.json()
    assert datos["valido"] is True
    assert datos["motivo"] is None
    assert datos["hora_fin"].startswith("11:00")
    assert float(datos["precio_turno"]) == 15000


def test_cancha_inexistente(cliente):
    r = validar(cliente, id_cancha=99)
    assert r.status_code == 200
    assert r.json()["valido"] is False
    assert r.json()["motivo"] == "CANCHA_INEXISTENTE"


def test_cancha_inactiva(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    cliente.delete("/api/v1/canchas/1")
    assert validar(cliente).json()["motivo"] == "CANCHA_INACTIVA"


def test_fecha_pasada(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    ayer = str(date.today() - timedelta(days=1))
    assert validar(cliente, fecha=ayer).json()["motivo"] == "FECHA_PASADA"


def test_hora_que_no_es_inicio_de_turno(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    # los turnos empiezan 08:00, 09:30, 11:00...; 10:00 no es inicio de ninguno
    assert validar(cliente, hora="10:00").json()["motivo"] == "HORARIO_INVALIDO"


def test_hora_fuera_del_horario(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    assert validar(cliente, hora="23:00").json()["motivo"] == "HORARIO_INVALIDO"


def test_turno_bloqueado(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    cliente.post("/api/v1/canchas/1/bloqueos",
                 json={"fecha": FECHA, "hora_desde": "09:00", "hora_hasta": "10:00", "motivo": "Mantenimiento"})
    assert validar(cliente).json()["motivo"] == "TURNO_BLOQUEADO"


def test_parametros_con_formato_invalido_dan_422(cliente):
    r = cliente.get("/api/v1/canchas/1/turnos/validar?fecha=ayer&hora_inicio=cualquiera")
    assert r.status_code == 422
