from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import obtener_sesion
from app.modelos.bloqueo import Bloqueo, BloqueoEntrada
from app.controladores import controlador_bloqueos as ctrl
from app.controladores.controlador_canchas import CanchaNoEncontrada

# ===== CAPA DE RUTAS: Bloqueos =====
# Los bloqueos se crean y listan como subrecurso de una cancha,
# y se eliminan por su propio id.

router = APIRouter(prefix="/api/v1", tags=["Bloqueos"])


@router.post(
    "/canchas/{id_cancha}/bloqueos",
    response_model=Bloqueo,
    status_code=201,
    responses={
        404: {"description": "Cancha no encontrada"},
        409: {"description": "Cancha inactiva o franja superpuesta con otro bloqueo"},
        422: {"description": "Datos inválidos, fecha pasada o fuera del horario de la cancha"},
    },
)
def crear(id_cancha: int, datos: BloqueoEntrada, sesion: Session = Depends(obtener_sesion)):
    try:
        return ctrl.crear_bloqueo(sesion, id_cancha, datos)
    except CanchaNoEncontrada:
        raise HTTPException(404, "Cancha no encontrada")
    except ctrl.CanchaInactiva:
        raise HTTPException(409, "La cancha está dada de baja")
    except ctrl.BloqueoSuperpuesto:
        raise HTTPException(409, "La franja se superpone con otro bloqueo")
    except ctrl.FechaPasada:
        raise HTTPException(422, "No se puede bloquear una fecha pasada")
    except ctrl.FueraDeHorario:
        raise HTTPException(422, "La franja está fuera del horario de la cancha")


@router.get(
    "/canchas/{id_cancha}/bloqueos",
    response_model=list[Bloqueo],
    responses={404: {"description": "Cancha no encontrada"}},
)
def listar(id_cancha: int, fecha: date | None = None, sesion: Session = Depends(obtener_sesion)):
    try:
        return ctrl.listar_bloqueos(sesion, id_cancha, fecha)
    except CanchaNoEncontrada:
        raise HTTPException(404, "Cancha no encontrada")


@router.delete(
    "/bloqueos/{id_bloqueo}",
    status_code=204,
    responses={404: {"description": "Bloqueo no encontrado"}},
)
def eliminar(id_bloqueo: int, sesion: Session = Depends(obtener_sesion)):
    """Elimina el bloqueo y la franja vuelve a quedar disponible."""
    try:
        ctrl.eliminar_bloqueo(sesion, id_bloqueo)
    except ctrl.BloqueoNoEncontrado:
        raise HTTPException(404, "Bloqueo no encontrado")
