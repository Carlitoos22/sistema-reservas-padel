from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.datos.tablas import OcupacionTabla, EventoProcesadoTabla

# ===== CAPA DE DATOS: Ocupaciones y eventos procesados =====
# Estas funciones no hacen commit: el controlador confirma todo junto
# en una sola transacción (el cambio de ocupación + el registro del evento).


def evento_ya_procesado(sesion: Session, event_id: str) -> bool:
    return sesion.get(EventoProcesadoTabla, event_id) is not None


def registrar_evento(sesion: Session, event_id: str, tipo: str):
    sesion.add(EventoProcesadoTabla(event_id=event_id, tipo=tipo, procesado_en=datetime.now()))


def buscar_por_reserva(sesion: Session, reserva_id: int):
    return sesion.scalars(select(OcupacionTabla).where(OcupacionTabla.reserva_id == reserva_id)).first()


def agregar(sesion: Session, datos: dict, activa: bool):
    sesion.add(OcupacionTabla(**datos, activa=activa))


def listar_activas(sesion: Session, cancha_id: int, fecha: date):
    consulta = select(OcupacionTabla).where(
        OcupacionTabla.cancha_id == cancha_id,
        OcupacionTabla.fecha == fecha,
        OcupacionTabla.activa.is_(True),
    )
    return sesion.scalars(consulta).all()
