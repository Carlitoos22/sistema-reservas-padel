from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import obtener_sesion
from app.modelos.cancha import Cancha, CanchaEntrada
from app.controladores import controlador_canchas as ctrl

# ===== CAPA DE RUTAS =====
# Endpoints HTTP del recurso "canchas". Traduce las excepciones
# del controlador a códigos de estado.

router = APIRouter(prefix="/api/v1/canchas", tags=["Canchas"])

NO_ENCONTRADA = {404: {"description": "Cancha no encontrada"}}
DUPLICADA = {409: {"description": "Ya existe una cancha con ese nombre"}}


@router.get("", response_model=list[Cancha])
def listar(incluir_inactivas: bool = False, sesion: Session = Depends(obtener_sesion)):
    return ctrl.listar_canchas(sesion, incluir_inactivas)


@router.get("/{id_cancha}", response_model=Cancha, responses=NO_ENCONTRADA)
def obtener(id_cancha: int, sesion: Session = Depends(obtener_sesion)):
    try:
        return ctrl.obtener_cancha(sesion, id_cancha)
    except ctrl.CanchaNoEncontrada:
        raise HTTPException(404, "Cancha no encontrada")


@router.post("", response_model=Cancha, status_code=201, responses=DUPLICADA)
def crear(datos: CanchaEntrada, sesion: Session = Depends(obtener_sesion)):
    try:
        return ctrl.crear_cancha(sesion, datos)
    except ctrl.NombreDuplicado:
        raise HTTPException(409, "Ya existe una cancha con ese nombre")


@router.put("/{id_cancha}", response_model=Cancha, responses={**NO_ENCONTRADA, **DUPLICADA})
def actualizar(id_cancha: int, datos: CanchaEntrada, sesion: Session = Depends(obtener_sesion)):
    try:
        return ctrl.actualizar_cancha(sesion, id_cancha, datos)
    except ctrl.CanchaNoEncontrada:
        raise HTTPException(404, "Cancha no encontrada")
    except ctrl.NombreDuplicado:
        raise HTTPException(409, "Ya existe una cancha con ese nombre")


@router.delete("/{id_cancha}", status_code=204, responses=NO_ENCONTRADA)
def dar_de_baja(id_cancha: int, sesion: Session = Depends(obtener_sesion)):
    """Baja lógica: la cancha deja de listarse pero no se borra de la base."""
    try:
        ctrl.dar_de_baja_cancha(sesion, id_cancha)
    except ctrl.CanchaNoEncontrada:
        raise HTTPException(404, "Cancha no encontrada")
