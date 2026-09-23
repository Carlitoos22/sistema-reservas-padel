from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.db import obtener_sesion
from app.modelos.disponibilidad import Disponibilidad
from app.controladores import controlador_disponibilidad as ctrl
from app.controladores.controlador_canchas import CanchaNoEncontrada
from app.controladores.controlador_bloqueos import CanchaInactiva, FechaPasada

# ===== CAPA DE RUTAS: Disponibilidad =====

router = APIRouter(prefix="/api/v1", tags=["Disponibilidad"])


@router.get(
    "/canchas/{id_cancha}/disponibilidad",
    response_model=Disponibilidad,
    responses={
        404: {"description": "Cancha no encontrada"},
        409: {"description": "La cancha está dada de baja"},
        422: {"description": "Fecha inválida o pasada"},
    },
)
def consultar(id_cancha: int, fecha: date, response: Response, sesion: Session = Depends(obtener_sesion)):
    """Devuelve todos los turnos de la cancha para la fecha, con su estado.

    El header de respuesta `X-Cache` indica si el resultado salió de Redis (HIT)
    o se calculó desde la base (MISS).
    """
    try:
        disponibilidad, origen = ctrl.consultar_disponibilidad(sesion, id_cancha, fecha)
        response.headers["X-Cache"] = origen
        return disponibilidad
    except CanchaNoEncontrada:
        raise HTTPException(404, "Cancha no encontrada")
    except CanchaInactiva:
        raise HTTPException(409, "La cancha está dada de baja")
    except FechaPasada:
        raise HTTPException(422, "No se puede consultar una fecha pasada")
