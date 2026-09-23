from datetime import date, time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import obtener_sesion
from app.modelos.validacion import ResultadoValidacion
from app.controladores import controlador_validacion as ctrl

# ===== CAPA DE RUTAS: Validación de turno =====
# Endpoint pensado para ser consumido por otro servicio (Reservas),
# no por el usuario final.

router = APIRouter(prefix="/api/v1", tags=["Integración con Reservas"])


@router.get("/canchas/{id_cancha}/turnos/validar", response_model=ResultadoValidacion)
def validar(id_cancha: int, fecha: date, hora_inicio: time, sesion: Session = Depends(obtener_sesion)):
    """Indica si el turno existe y está disponible para reservar.

    Siempre responde 200 cuando los parámetros tienen formato válido;
    si el turno no se puede reservar, `valido` es false y `motivo` explica por qué.
    Si es válido, devuelve además la hora de fin y el precio del turno.
    """
    return ctrl.validar_turno(sesion, id_cancha, fecha, hora_inicio)
