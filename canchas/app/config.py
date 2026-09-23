import os
from dotenv import load_dotenv

# ===== CONFIGURACIÓN =====
# Todo lo que depende del entorno sale de variables de entorno (.env),
# nada queda escrito en el código.

load_dotenv()

NOMBRE_APP = os.getenv("NOMBRE_APP", "Servicio de Canchas")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://canchas:canchas@localhost:5433/canchas")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
CACHE_TTL_SEGUNDOS = int(os.getenv("CACHE_TTL_SEGUNDOS", "300"))
