from decimal import Decimal
from datetime import time
from sqlalchemy import String, Boolean, Numeric, Time, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

# ===== TABLAS DE LA BASE DE DATOS =====
# Definen cómo se guardan los datos en PostgreSQL.
# Son internas del módulo: la API nunca las expone directamente.


class CanchaTabla(Base):
    __tablename__ = "canchas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    tipo: Mapped[str] = mapped_column(String(20))
    techada: Mapped[bool] = mapped_column(Boolean, default=False)
    precio_turno: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    hora_apertura: Mapped[time] = mapped_column(Time)
    hora_cierre: Mapped[time] = mapped_column(Time)
    duracion_turno_min: Mapped[int] = mapped_column(Integer)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
