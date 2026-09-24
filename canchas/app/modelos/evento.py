from datetime import date, datetime, time
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, model_validator

# ===== MODELOS: Eventos del módulo de Reservas =====
# Contrato de los mensajes que llegan por RabbitMQ. Si un mensaje no
# cumple este formato, no se reintenta: va directo a la cola de fallidos.


class TipoEvento(str, Enum):
    reserva_creada = "ReservaCreada"
    reserva_cancelada = "ReservaCancelada"


class DatosReserva(BaseModel):
    reserva_id: int
    cancha_id: int
    fecha: date
    hora_inicio: time
    hora_fin: time

    @model_validator(mode="after")
    def validar_franja(self):
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("hora_fin debe ser posterior a hora_inicio")
        return self


class EventoReserva(BaseModel):
    event_id: UUID              # clave de idempotencia
    tipo: TipoEvento
    ocurrido_en: datetime
    correlation_id: str         # permite seguir la reserva entre servicios en los logs
    datos: DatosReserva
