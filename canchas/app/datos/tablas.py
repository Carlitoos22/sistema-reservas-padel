from decimal import Decimal
from datetime import date, time, datetime
from sqlalchemy import String, Boolean, Numeric, Time, Integer, Date, DateTime, ForeignKey, Text
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


class BloqueoTabla(Base):
    __tablename__ = "bloqueos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cancha_id: Mapped[int] = mapped_column(ForeignKey("canchas.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    hora_desde: Mapped[time] = mapped_column(Time)
    hora_hasta: Mapped[time] = mapped_column(Time)
    motivo: Mapped[str] = mapped_column(String(100))


class OcupacionTabla(Base):
    """Copia local y mínima de las reservas, construida solo a partir de eventos.
    El módulo no lee la base de Reservas: se entera de la ocupación por RabbitMQ."""
    __tablename__ = "ocupaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    reserva_id: Mapped[int] = mapped_column(Integer, unique=True)
    cancha_id: Mapped[int] = mapped_column(Integer, index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fin: Mapped[time] = mapped_column(Time)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class EventoProcesadoTabla(Base):
    """Registro de eventos ya aplicados. Su clave primaria es el event_id:
    si el mismo evento llega dos veces, el segundo se descarta (idempotencia)."""
    __tablename__ = "eventos_procesados"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30))
    procesado_en: Mapped[datetime] = mapped_column(DateTime)


class OutboxTabla(Base):
    """Bandeja de salida (patrón Transactional Outbox).
    El evento se guarda en la MISMA transacción que el cambio de negocio;
    otro proceso (app/publicador.py) lo lee y lo publica en RabbitMQ.
    Así nunca queda un bloqueo guardado sin su evento, ni un evento
    publicado de un bloqueo que finalmente no se guardó."""
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True)
    tipo: Mapped[str] = mapped_column(String(30))
    routing_key: Mapped[str] = mapped_column(String(50))
    cuerpo: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime)
    publicado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
