import redis

# ===== CONEXIÓN A REDIS =====
# Redis se usa como memoria rápida temporal, para:
#  - bloquear turnos (evitar doble reserva)
#  - registrar claves de idempotencia
# Coincide con el puerto definido en docker-compose.yml (6379)

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True   # devuelve texto en vez de bytes
)
