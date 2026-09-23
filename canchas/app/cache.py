import logging
import redis
from app.config import REDIS_URL, CACHE_TTL_SEGUNDOS

# ===== CACHÉ DE DISPONIBILIDAD (Redis) =====
# Patrón cache-aside: se consulta primero Redis; si no está (MISS) se calcula
# desde la base y se guarda con un TTL. Cuando algo que afecta la disponibilidad
# cambia, se invalida la clave para que la próxima consulta recalcule.
#
# Redis es una optimización, no la fuente de verdad: si Redis no responde,
# el servicio sigue funcionando calculando todo desde PostgreSQL.

log = logging.getLogger("canchas.cache")

PREFIJO = "canchas:disponibilidad"

_cliente = None


def obtener_cliente():
    global _cliente
    if _cliente is None:
        _cliente = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1)
    return _cliente


def usar_cliente(cliente):
    """Permite reemplazar el cliente (se usa en los tests)."""
    global _cliente
    _cliente = cliente


def clave_disponibilidad(cancha_id: int, fecha) -> str:
    return f"{PREFIJO}:{cancha_id}:{fecha}"


def leer(clave: str):
    try:
        return obtener_cliente().get(clave)
    except redis.RedisError:
        log.warning("Redis no disponible al leer %s; se calcula desde la base", clave)
        return None


def guardar(clave: str, valor: str):
    try:
        obtener_cliente().set(clave, valor, ex=CACHE_TTL_SEGUNDOS)
    except redis.RedisError:
        log.warning("Redis no disponible al guardar %s", clave)


def invalidar_fecha(cancha_id: int, fecha):
    """Un bloqueo nuevo o eliminado solo afecta la disponibilidad de ese día."""
    try:
        obtener_cliente().delete(clave_disponibilidad(cancha_id, fecha))
    except redis.RedisError:
        log.warning("Redis no disponible al invalidar cancha %s fecha %s", cancha_id, fecha)


def invalidar_cancha(cancha_id: int):
    """Un cambio en la cancha (horario, baja) afecta todas sus fechas cacheadas."""
    try:
        cliente = obtener_cliente()
        for clave in cliente.scan_iter(f"{PREFIJO}:{cancha_id}:*"):
            cliente.delete(clave)
    except redis.RedisError:
        log.warning("Redis no disponible al invalidar cancha %s", cancha_id)
