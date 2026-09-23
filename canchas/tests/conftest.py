import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, obtener_sesion
from app.datos import tablas  # noqa: F401

# Los tests usan una base SQLite en memoria: son rápidos y no necesitan Docker.
# Cada test arranca con la base vacía.


@pytest.fixture
def cliente():
    motor = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(motor)
    Sesion = sessionmaker(bind=motor)

    def sesion_de_prueba():
        sesion = Sesion()
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[obtener_sesion] = sesion_de_prueba
    yield TestClient(app)
    app.dependency_overrides.clear()
