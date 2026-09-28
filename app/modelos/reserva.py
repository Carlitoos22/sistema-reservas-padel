from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from app.database import Base

# ===== MODELO PYDANTIC (validación de la API) =====
# Esto valida los datos que entran por las peticiones.

class ReservaBase(BaseModel):
    nombre_jugador: str
    cancha: str
    fecha: str
    hora: str
    estado: str = "pendiente"


class Reserva(ReservaBase):
    id: int

    class Config:
        from_attributes = True   # permite convertir desde el modelo de la tabla


# ===== MODELO SQLALCHEMY (la tabla en PostgreSQL) =====
# Esto describe cómo es la tabla "reservas" en la base de datos.

class ReservaDB(Base):
    __tablename__ = "reservas"

    id = Column(Integer, primary_key=True, index=True)
    nombre_jugador = Column(String, nullable=False)
    cancha = Column(String, nullable=False)
    fecha = Column(String, nullable=False)
    hora = Column(String, nullable=False)
    estado = Column(String, default="pendiente")