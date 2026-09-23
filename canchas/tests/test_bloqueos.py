# Pruebas de bloqueos de franjas horarias (RF-C3)
from datetime import date, timedelta
from tests.test_canchas import CANCHA

FECHA = str(date.today() + timedelta(days=7))
BLOQUEO = {"fecha": FECHA, "hora_desde": "14:00", "hora_hasta": "18:00", "motivo": "Mantenimiento"}


def crear_cancha(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)  # abre 08:00, cierra 23:30


def bloquear(cliente, id_cancha=1, **cambios):
    return cliente.post(f"/api/v1/canchas/{id_cancha}/bloqueos", json={**BLOQUEO, **cambios})


def test_crear_bloqueo(cliente):
    crear_cancha(cliente)
    r = bloquear(cliente)
    assert r.status_code == 201
    assert r.json()["cancha_id"] == 1


def test_bloqueo_en_cancha_inexistente_da_404(cliente):
    assert bloquear(cliente, id_cancha=99).status_code == 404


def test_bloqueo_en_cancha_inactiva_da_409(cliente):
    crear_cancha(cliente)
    cliente.delete("/api/v1/canchas/1")
    assert bloquear(cliente).status_code == 409


def test_hora_hasta_antes_de_desde_da_422(cliente):
    crear_cancha(cliente)
    assert bloquear(cliente, hora_desde="18:00", hora_hasta="14:00").status_code == 422


def test_fuera_del_horario_de_la_cancha_da_422(cliente):
    crear_cancha(cliente)
    assert bloquear(cliente, hora_desde="06:00", hora_hasta="09:00").status_code == 422


def test_fecha_pasada_da_422(cliente):
    crear_cancha(cliente)
    ayer = str(date.today() - timedelta(days=1))
    assert bloquear(cliente, fecha=ayer).status_code == 422


def test_bloqueo_superpuesto_da_409(cliente):
    crear_cancha(cliente)
    bloquear(cliente)  # 14:00 a 18:00
    assert bloquear(cliente, hora_desde="17:00", hora_hasta="20:00").status_code == 409


def test_bloqueos_contiguos_se_permiten(cliente):
    crear_cancha(cliente)
    bloquear(cliente)  # 14:00 a 18:00
    # empieza justo cuando termina el otro: no se superponen
    assert bloquear(cliente, hora_desde="18:00", hora_hasta="20:00").status_code == 201


def test_mismo_horario_otro_dia_se_permite(cliente):
    crear_cancha(cliente)
    bloquear(cliente)
    otro_dia = str(date.today() + timedelta(days=8))
    assert bloquear(cliente, fecha=otro_dia).status_code == 201


def test_listar_bloqueos_por_fecha(cliente):
    crear_cancha(cliente)
    bloquear(cliente)
    bloquear(cliente, fecha=str(date.today() + timedelta(days=8)))
    assert len(cliente.get("/api/v1/canchas/1/bloqueos").json()) == 2
    assert len(cliente.get(f"/api/v1/canchas/1/bloqueos?fecha={FECHA}").json()) == 1


def test_eliminar_bloqueo_libera_la_franja(cliente):
    crear_cancha(cliente)
    bloquear(cliente)
    assert cliente.delete("/api/v1/bloqueos/1").status_code == 204
    assert cliente.get("/api/v1/canchas/1/bloqueos").json() == []
    # la franja quedó libre: se puede volver a bloquear
    assert bloquear(cliente).status_code == 201


def test_eliminar_bloqueo_inexistente_da_404(cliente):
    assert cliente.delete("/api/v1/bloqueos/99").status_code == 404
