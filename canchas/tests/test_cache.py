# Pruebas de la caché de disponibilidad en Redis
from datetime import date, timedelta
import redis
from app import cache
from app.config import CACHE_TTL_SEGUNDOS
from tests.test_canchas import CANCHA

FECHA = str(date.today() + timedelta(days=7))
CLAVE = f"canchas:disponibilidad:1:{FECHA}"
URL = f"/api/v1/canchas/1/disponibilidad?fecha={FECHA}"


def bloquear(cliente, desde="14:00", hasta="18:00"):
    return cliente.post("/api/v1/canchas/1/bloqueos",
                        json={"fecha": FECHA, "hora_desde": desde, "hora_hasta": hasta, "motivo": "Torneo"})


def estados(respuesta):
    return {t["hora_inicio"][:5]: t["estado"] for t in respuesta.json()["turnos"]}


def test_primera_consulta_miss_segunda_hit(cliente, redis_falso):
    cliente.post("/api/v1/canchas", json=CANCHA)
    assert cliente.get(URL).headers["X-Cache"] == "MISS"
    assert cliente.get(URL).headers["X-Cache"] == "HIT"
    assert redis_falso.exists(CLAVE)


def test_la_clave_se_guarda_con_ttl(cliente, redis_falso):
    cliente.post("/api/v1/canchas", json=CANCHA)
    cliente.get(URL)
    ttl = redis_falso.ttl(CLAVE)
    assert 0 < ttl <= CACHE_TTL_SEGUNDOS


def test_al_expirar_vuelve_a_calcular(cliente, redis_falso):
    cliente.post("/api/v1/canchas", json=CANCHA)
    cliente.get(URL)
    redis_falso.delete(CLAVE)  # equivale a que se cumpla el TTL
    assert cliente.get(URL).headers["X-Cache"] == "MISS"


def test_crear_bloqueo_invalida_la_cache(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    cliente.get(URL)  # queda cacheado todo libre
    bloquear(cliente)
    r = cliente.get(URL)
    assert r.headers["X-Cache"] == "MISS"
    assert estados(r)["14:00"] == "bloqueado"  # no se sirvió el dato viejo


def test_eliminar_bloqueo_invalida_la_cache(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    bloquear(cliente)
    cliente.get(URL)  # queda cacheado con el bloqueo
    cliente.delete("/api/v1/bloqueos/1")
    r = cliente.get(URL)
    assert r.headers["X-Cache"] == "MISS"
    assert estados(r)["14:00"] == "libre"


def test_bloqueo_de_otra_fecha_no_invalida(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    cliente.get(URL)
    otro_dia = str(date.today() + timedelta(days=8))
    cliente.post("/api/v1/canchas/1/bloqueos",
                 json={"fecha": otro_dia, "hora_desde": "14:00", "hora_hasta": "18:00", "motivo": "Torneo"})
    assert cliente.get(URL).headers["X-Cache"] == "HIT"


def test_modificar_cancha_invalida_todas_sus_fechas(cliente, redis_falso):
    cliente.post("/api/v1/canchas", json=CANCHA)
    otro_dia = str(date.today() + timedelta(days=8))
    cliente.get(URL)
    cliente.get(f"/api/v1/canchas/1/disponibilidad?fecha={otro_dia}")
    cliente.put("/api/v1/canchas/1", json={**CANCHA, "duracion_turno_min": 60})
    assert list(redis_falso.scan_iter("canchas:disponibilidad:1:*")) == []
    r = cliente.get(URL)
    assert r.headers["X-Cache"] == "MISS"
    assert len(r.json()["turnos"]) == 15  # ahora con turnos de 60 minutos


def test_baja_de_cancha_no_sirve_cache(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    cliente.get(URL)
    cliente.delete("/api/v1/canchas/1")
    assert cliente.get(URL).status_code == 409


class RedisCaido:
    """Simula un Redis que no responde."""
    def get(self, *a, **k): raise redis.ConnectionError("caído")
    def set(self, *a, **k): raise redis.ConnectionError("caído")
    def delete(self, *a, **k): raise redis.ConnectionError("caído")
    def scan_iter(self, *a, **k): raise redis.ConnectionError("caído")


def test_si_redis_se_cae_el_servicio_sigue_funcionando(cliente):
    cliente.post("/api/v1/canchas", json=CANCHA)
    cache.usar_cliente(RedisCaido())
    r = cliente.get(URL)
    assert r.status_code == 200
    assert r.headers["X-Cache"] == "MISS"
    assert bloquear(cliente).status_code == 201  # tampoco falla al invalidar
