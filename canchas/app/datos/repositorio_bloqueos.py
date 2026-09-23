from datetime import date, time
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.datos.tablas import BloqueoTabla

# ===== CAPA DE DATOS: Repositorio de Bloqueos =====


def listar_por_cancha(sesion: Session, cancha_id: int, fecha: date | None = None):
    consulta = select(BloqueoTabla).where(BloqueoTabla.cancha_id == cancha_id)
    if fecha is not None:
        consulta = consulta.where(BloqueoTabla.fecha == fecha)
    return sesion.scalars(consulta.order_by(BloqueoTabla.fecha, BloqueoTabla.hora_desde)).all()


def buscar_superpuestos(sesion: Session, cancha_id: int, fecha: date, desde: time, hasta: time):
    """Dos franjas se superponen si una empieza antes de que termine la otra, y viceversa."""
    consulta = select(BloqueoTabla).where(
        BloqueoTabla.cancha_id == cancha_id,
        BloqueoTabla.fecha == fecha,
        BloqueoTabla.hora_desde < hasta,
        BloqueoTabla.hora_hasta > desde,
    )
    return sesion.scalars(consulta).all()


def buscar_por_id(sesion: Session, id_bloqueo: int):
    return sesion.get(BloqueoTabla, id_bloqueo)


def crear(sesion: Session, cancha_id: int, datos: dict):
    bloqueo = BloqueoTabla(cancha_id=cancha_id, **datos)
    sesion.add(bloqueo)
    sesion.commit()
    sesion.refresh(bloqueo)
    return bloqueo


def eliminar(sesion: Session, bloqueo: BloqueoTabla):
    sesion.delete(bloqueo)
    sesion.commit()
