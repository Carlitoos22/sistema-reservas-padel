from pydantic import BaseModel, field_validator
from sqlalchemy import Column, Integer, String
from app.validaciones import validar_texto_seguro
from app.database import Base


class ReservaBase(BaseModel):
    nombre_jugador: str
    cancha: str
    fecha: str
    hora: str
    estado: str = "pendiente"
    usuario_email: str | None = None   # dueño real de la reserva (email, único)

    @field_validator("nombre_jugador", "cancha", "estado")
    @classmethod
    def _sin_caracteres_peligrosos(cls, v):
        return validar_texto_seguro(v)


class Reserva(ReservaBase):
    id: int

    class Config:
        from_attributes = True


class ReservaDB(Base):
    __tablename__ = "reservas"
    id = Column(Integer, primary_key=True, index=True)
    nombre_jugador = Column(String, nullable=False)
    cancha = Column(String, nullable=False)
    fecha = Column(String, nullable=False)
    hora = Column(String, nullable=False)
    estado = Column(String, default="pendiente")
    usuario_email = Column(String, nullable=True)
