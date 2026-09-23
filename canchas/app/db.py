from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import DATABASE_URL

# ===== CONEXIÓN A LA BASE DE DATOS =====
# Base propia del módulo de Canchas: ningún otro servicio accede a ella.

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SesionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def obtener_sesion():
    """Dependencia de FastAPI: abre una sesión por pedido y la cierra al terminar."""
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()
