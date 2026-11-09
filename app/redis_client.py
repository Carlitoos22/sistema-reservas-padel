import os
import redis

# ===== CONEXION A REDIS =====
# Redis se usa como memoria rapida temporal, para:
#  - bloquear turnos (evitar doble reserva)
#  - registrar claves de idempotencia
# En local usa localhost:6379; en la nube usa la variable REDIS_URL.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)