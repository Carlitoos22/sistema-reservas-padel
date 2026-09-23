from datetime import date, time
from pydantic import BaseModel, Field, model_validator, ConfigDict

# ===== MODELOS: Bloqueo =====
# Un bloqueo reserva una franja horaria de una cancha para uso interno
# (mantenimiento, torneo) y hace que no se ofrezca como disponible.


class BloqueoEntrada(BaseModel):
    fecha: date = Field(examples=["2026-10-15"])
    hora_desde: time = Field(examples=["14:00"])
    hora_hasta: time = Field(examples=["18:00"])
    motivo: str = Field(min_length=1, max_length=100, examples=["Mantenimiento del césped"])

    @model_validator(mode="after")
    def validar_franja(self):
        if self.hora_hasta <= self.hora_desde:
            raise ValueError("hora_hasta debe ser posterior a hora_desde")
        return self


class Bloqueo(BloqueoEntrada):
    id: int
    cancha_id: int

    model_config = ConfigDict(from_attributes=True)
