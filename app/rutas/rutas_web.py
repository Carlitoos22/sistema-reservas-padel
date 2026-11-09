from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date

from app.database import get_db
from app.plantillas import templates
from app.seguridad import usuario_actual
from app.controladores import controlador_reservas
from app.modelos.reserva import ReservaBase
from app.datos.canchas_demo import CANCHAS, HORARIOS

router = APIRouter(tags=["Web"])


@router.get("/canchas", response_class=HTMLResponse)
def ver_canchas(request: Request, fecha: str = "", msg: str = "", db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if usuario is None:
        return RedirectResponse(url="/login", status_code=303)

    if not fecha:
        fecha = date.today().isoformat()

    reservas = controlador_reservas.listar_reservas(db)
    ocupados = {(r.cancha, r.fecha, r.hora) for r in reservas}

    canchas = []
    for c in CANCHAS:
        turnos = [{"hora": h, "ocupado": (c["nombre"], fecha, h) in ocupados} for h in HORARIOS]
        canchas.append({"nombre": c["nombre"], "tipo": c["tipo"], "turnos": turnos})

    return templates.TemplateResponse(
        request, "canchas.html",
        {"usuario": usuario, "canchas": canchas, "fecha": fecha, "msg": msg},
    )


@router.post("/reservar")
def reservar(request: Request, cancha: str = Form(...), fecha: str = Form(...),
             hora: str = Form(...), db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if usuario is None:
        return RedirectResponse(url="/login", status_code=303)

    datos = ReservaBase(nombre_jugador=usuario.nombre, cancha=cancha, fecha=fecha, hora=hora)
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
    mias = [r for r in todas if r.nombre_jugador == usuario.nombre]
    return templates.TemplateResponse(
        request, "mis_reservas.html",
        {"usuario": usuario, "reservas": mias},
    )


@router.post("/cancelar/{id_reserva}")
def cancelar(request: Request, id_reserva: int, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if usuario is None:
        return RedirectResponse(url="/login", status_code=303)

    # Control de titularidad (IDOR/BOLA): solo cancela si la reserva es tuya
    reserva = controlador_reservas.obtener_reserva(db, id_reserva)
    if reserva and reserva.nombre_jugador == usuario.nombre:
        controlador_reservas.eliminar_reserva(db, id_reserva)
    return RedirectResponse(url="/mis-reservas", status_code=303)