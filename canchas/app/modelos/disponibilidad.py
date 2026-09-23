from datetime import date, time
from enum import Enum
from pydantic import BaseModel

# ===== MODELOS: Disponibilidad =====
# Turno no es una tabla: se calcula en cada consulta a partir del horario
# de la cancha. Estos modelos solo definen cómo se devuelve en la API.


class EstadoTurno(str, Enum):
    libre = "libre"
    bloqueado = "bloqueado"
    ocupado = "ocupado"  # se completa con los eventos del módulo de Reservas


class Turno(BaseModel):
    hora_inicio: time
    hora_fin: time
    estado: EstadoTurno


class Disponibilidad(BaseModel):
    cancha_id: int
    fecha: date
    turnos: list[Turno]
