from datetime import date
from sqlalchemy.orm import Session
from app.datos import repositorio_bloqueos, repositorio_canchas
from app.modelos.bloqueo import BloqueoEntrada
from app.controladores.controlador_canchas import CanchaNoEncontrada

# ===== CAPA DE CONTROLADORES: Bloqueos =====


class CanchaInactiva(Exception):
    pass


class FueraDeHorario(Exception):
    pass


class FechaPasada(Exception):
    pass


class BloqueoSuperpuesto(Exception):
    pass


class BloqueoNoEncontrado(Exception):
    pass


def crear_bloqueo(sesion: Session, id_cancha: int, datos: BloqueoEntrada):
    # Se toma la cancha con FOR UPDATE: si llegan dos bloqueos simultáneos
    # para la misma cancha, el segundo espera a que el primero termine y
    # recién ahí busca superposiciones, así que ve el bloqueo ya guardado.
    cancha = repositorio_canchas.buscar_por_id_para_modificar(sesion, id_cancha)
    if cancha is None:
        raise CanchaNoEncontrada()
    if not cancha.activa:
        raise CanchaInactiva()
    if datos.fecha < date.today():
        raise FechaPasada()
    if datos.hora_desde < cancha.hora_apertura or datos.hora_hasta > cancha.hora_cierre:
        raise FueraDeHorario()
    if repositorio_bloqueos.buscar_superpuestos(
        sesion, id_cancha, datos.fecha, datos.hora_desde, datos.hora_hasta
    ):
        raise BloqueoSuperpuesto()
    return repositorio_bloqueos.crear(sesion, id_cancha, datos.model_dump())


def listar_bloqueos(sesion: Session, id_cancha: int, fecha: date | None):
    if repositorio_canchas.buscar_por_id(sesion, id_cancha) is None:
        raise CanchaNoEncontrada()
    return repositorio_bloqueos.listar_por_cancha(sesion, id_cancha, fecha)


def eliminar_bloqueo(sesion: Session, id_bloqueo: int):
    bloqueo = repositorio_bloqueos.buscar_por_id(sesion, id_bloqueo)
    if bloqueo is None:
        raise BloqueoNoEncontrado()
    repositorio_bloqueos.eliminar(sesion, bloqueo)
