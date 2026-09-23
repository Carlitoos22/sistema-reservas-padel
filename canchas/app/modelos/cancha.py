from datetime import time, datetime, date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, model_validator, ConfigDict

# ===== MODELOS: Cancha =====
# Definen el contrato de la API: qué datos entran, con qué validaciones,
# y qué datos salen. A diferencia del AE1, cada campo tiene su tipo real.


class TipoCancha(str, Enum):
    cristal = "cristal"
    muro = "muro"


class CanchaEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=50, examples=["Cancha 1"])
    tipo: TipoCancha
    techada: bool = False
    precio_turno: Decimal = Field(gt=0, max_digits=10, decimal_places=2, examples=[15000])
    hora_apertura: time = Field(examples=["08:00"])
    hora_cierre: time = Field(examples=["23:30"])
    duracion_turno_min: int = Field(ge=30, le=180, examples=[90])

    @model_validator(mode="after")
    def validar_horario(self):
        """La cancha tiene que cerrar después de abrir y entrar al menos un turno."""
        if self.hora_cierre <= self.hora_apertura:
            raise ValueError("hora_cierre debe ser posterior a hora_apertura")
        apertura = datetime.combine(date.today(), self.hora_apertura)
        cierre = datetime.combine(date.today(), self.hora_cierre)
        minutos_abierta = (cierre - apertura).seconds // 60
        if minutos_abierta < self.duracion_turno_min:
            raise ValueError("el horario no alcanza para un turno completo")
        return self


class Cancha(CanchaEntrada):
    id: int
    activa: bool

    model_config = ConfigDict(from_attributes=True)
