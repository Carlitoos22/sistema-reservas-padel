from datetime import date, time
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel

# ===== MODELOS: Validación de turno =====
# Contrato que consume el módulo de Reservas antes de crear una reserva.
# La consulta siempre responde 200 si los parámetros son correctos:
# "el turno no es válido" es una respuesta, no un error del servicio.


class MotivoRechazo(str, Enum):
    cancha_inexistente = "CANCHA_INEXISTENTE"
    cancha_inactiva = "CANCHA_INACTIVA"
    fecha_pasada = "FECHA_PASADA"
    horario_invalido = "HORARIO_INVALIDO"  # no coincide con el inicio de ningún turno
    turno_bloqueado = "TURNO_BLOQUEADO"


class ResultadoValidacion(BaseModel):
    valido: bool
    motivo: MotivoRechazo | None = None
    cancha_id: int
    fecha: date
    hora_inicio: time
    hora_fin: time | None = None
    precio_turno: Decimal | None = None
