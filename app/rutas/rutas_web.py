from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta

from app.database import get_db
from app.plantillas import templates
from app.seguridad import usuario_actual
from app.controladores import controlador_reservas
from app.modelos.reserva import ReservaBase
from app.controladores import controlador_canchas
from app.controladores.controlador_canchas import HORARIOS

router = APIRouter(tags=["Web"])

# Minutos antes del turno hasta los que se permite cancelar
MINUTOS_LIMITE_CANCELACION = 30


def _inicio(bloque: str) -> str:
    return bloque.split(" - ")[0].strip()


def _inicio_dt(fecha: str, bloque: str) -> datetime:
    return datetime.strptime(f"{fecha} {_inicio(bloque)}", "%Y-%m-%d %H:%M")


def _es_pasado(fecha: str, bloque: str) -> bool:
    try:
        return _inicio_dt(fecha, bloque) < datetime.now()
    except ValueError:
        return False


def _se_puede_cancelar(fecha: str, bloque: str) -> bool:
    """Se puede cancelar hasta 30 min antes del inicio del turno."""
    try:
        limite = _inicio_dt(fecha, bloque) - timedelta(minutes=MINUTOS_LIMITE_CANCELACION)
        return datetime.now() < limite
    except ValueError:
        return True


@router.get("/canchas", response_class=HTMLResponse)
def ver_canchas(request: Request, fecha: str = "", msg: str = "", db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if usuario is None:
        return RedirectResponse(url="/login", status_code=303)

    hoy = date.today().isoformat()
    if not fecha:
        fecha = hoy

    reservas = controlador_reservas.listar_reservas(db)
    ocupados = {(r.cancha, r.fecha, r.hora) for r in reservas}

    canchas = []
    for c in controlador_canchas.listar_canchas_activas(db):
        turnos = []
        for h in HORARIOS:
            if _es_pasado(fecha, h):
                continue
            turnos.append({"hora": h, "ocupado": (c.nombre, fecha, h) in ocupados})
        canchas.append({"nombre": c.nombre, "tipo": c.tipo, "turnos": turnos})

    return templates.TemplateResponse(
        request, "canchas.html",
        {"usuario": usuario, "canchas": canchas, "fecha": fecha, "msg": msg, "hoy": hoy},
    )


@router.post("/reservar")
def reservar(request: Request, cancha: str = Form(...), fecha: str = Form(...),
             hora: str = Form(...), db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if usuario is None:
        return RedirectResponse(url="/login", status_code=303)

    if _es_pasado(fecha, hora):
        return RedirectResponse(url=f"/canchas?fecha={fecha}&msg=pasado", status_code=303)

    if not controlador_canchas.es_reservable(db, cancha, hora):
        return RedirectResponse(url=f"/canchas?fecha={fecha}&msg=no_disponible", status_code=303)

    datos = ReservaBase(nombre_jugador=usuario.nombre, cancha=cancha, fecha=fecha,
                        hora=hora, usuario_email=usuario.email)
    try:
        controlador_reservas.crear_reserva(db, datos)
        msg = "ok"
    except HTTPException:
        msg = "ocupado"
    return RedirectResponse(url=f"/canchas?fecha={fecha}&msg={msg}", status_code=303)


@router.get("/mis-reservas", response_class=HTMLResponse)
def mis_reservas(request: Request, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if usuario is None:
        return RedirectResponse(url="/login", status_code=303)

    todas = controlador_reservas.listar_reservas(db)
    mias = [r for r in todas if r.usuario_email == usuario.email]
    for r in mias:
        r.cancelable = _se_puede_cancelar(r.fecha, r.hora)
        r.pasado = _es_pasado(r.fecha, r.hora)
    return templates.TemplateResponse(
        request, "mis_reservas.html",
        {"usuario": usuario, "reservas": mias},
    )


@router.post("/cancelar/{id_reserva}")
def cancelar(request: Request, id_reserva: int, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if usuario is None:
        return RedirectResponse(url="/login", status_code=303)

    # Solo cancela si es tuya y falta más de 30 min para el turno
    reserva = controlador_reservas.obtener_reserva(db, id_reserva)
    if (reserva and reserva.usuario_email == usuario.email
            and _se_puede_cancelar(reserva.fecha, reserva.hora)):
        controlador_reservas.eliminar_reserva(db, id_reserva)
    return RedirectResponse(url="/mis-reservas", status_code=303)
