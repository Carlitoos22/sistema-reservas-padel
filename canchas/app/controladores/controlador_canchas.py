from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.datos import repositorio_canchas
from app import cache
from app.modelos.cancha import CanchaEntrada

# ===== CAPA DE CONTROLADORES =====
# Reglas de negocio de las canchas. No sabe nada de HTTP:
# si algo falla, lanza una excepción propia y la ruta decide el código.


class CanchaNoEncontrada(Exception):
    pass


class NombreDuplicado(Exception):
    pass


def listar_canchas(sesion: Session, incluir_inactivas: bool):
    return repositorio_canchas.listar(sesion, incluir_inactivas)


def obtener_cancha(sesion: Session, id_cancha: int):
    cancha = repositorio_canchas.buscar_por_id(sesion, id_cancha)
    if cancha is None:
        raise CanchaNoEncontrada()
    return cancha


def crear_cancha(sesion: Session, datos: CanchaEntrada):
    if repositorio_canchas.buscar_por_nombre(sesion, datos.nombre):
        raise NombreDuplicado()
    try:
        return repositorio_canchas.crear(sesion, datos.model_dump())
    except IntegrityError:
        # Dos altas simultáneas con el mismo nombre: la restricción UNIQUE
        # de la base rechaza la segunda aunque ambas hayan pasado el chequeo.
        sesion.rollback()
        raise NombreDuplicado()


def actualizar_cancha(sesion: Session, id_cancha: int, datos: CanchaEntrada):
    cancha = obtener_cancha(sesion, id_cancha)
    otra = repositorio_canchas.buscar_por_nombre(sesion, datos.nombre)
    if otra and otra.id != id_cancha:
        raise NombreDuplicado()
    try:
        actualizada = repositorio_canchas.actualizar(sesion, cancha, datos.model_dump())
    except IntegrityError:
        sesion.rollback()
        raise NombreDuplicado()
    # Cambiar horario o duración cambia la grilla de todas las fechas.
    cache.invalidar_cancha(id_cancha)
    return actualizada


def dar_de_baja_cancha(sesion: Session, id_cancha: int):
    cancha = obtener_cancha(sesion, id_cancha)
    repositorio_canchas.dar_de_baja(sesion, cancha)
    cache.invalidar_cancha(id_cancha)
