from datetime import date
from fastapi import APIRouter, Depends, HTTPException
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
def consultar(id_cancha: int, fecha: date, sesion: Session = Depends(obtener_sesion)):
    """Devuelve todos los turnos de la cancha para la fecha, con su estado."""
    try:
        return ctrl.consultar_disponibilidad(sesion, id_cancha, fecha)
    except CanchaNoEncontrada:
        raise HTTPException(404, "Cancha no encontrada")
    except CanchaInactiva:
        raise HTTPException(409, "La cancha está dada de baja")
    except FechaPasada:
        raise HTTPException(422, "No se puede consultar una fecha pasada")
