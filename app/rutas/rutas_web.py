from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.database import get_db
from app.plantillas import templates
from app.seguridad import usuario_actual
from app.controladores import controlador_reservas
from app.modelos.reserva import ReservaBase
from app.datos.canchas_demo import CANCHAS, HORARIOS

router = APIRouter(tags=["Web"])


def _inicio(bloque: str) -> str:
    return bloque.split(" - ")[0].strip()


def _es_pasado(fecha: str, bloque: str) -> bool:
    try:
        momento = datetime.strptime(f"{fecha} {_inicio(bloque)}", "%Y-%m-%d %H:%M")
        return momento < datetime.now()
    except ValueError:
        return False


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
    for c in CANCHAS:
        turnos = []
        for h in HORARIOS:
            if _es_pasado(fecha, h):
                continue
            turnos.append({"hora": h, "ocupado": (c["nombre"], fecha, h) in ocupados})
        canchas.append({"nombre": c["nombre"], "tipo": c["tipo"], "turnos": turnos})

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
    for r in mias:
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

    reserva = controlador_reservas.obtener_reserva(db, id_reserva)
    if (reserva and reserva.nombre_jugador == usuario.nombre
            and not _es_pasado(reserva.fecha, reserva.hora)):
        controlador_reservas.eliminar_reserva(db, id_reserva)
    return RedirectResponse(url="/mis-reservas", status_code=303)