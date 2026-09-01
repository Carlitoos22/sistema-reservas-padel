from pydantic import BaseModel

# ===== MODELO: Reserva =====
# Define la estructura de una reserva y valida los datos de entrada.

class ReservaBase(BaseModel):
    nombre_jugador: str
    cancha: str
    fecha: str
    hora: str
    estado: str = "pendiente"   # valor por defecto si no lo mandan


class Reserva(ReservaBase):
    id: int