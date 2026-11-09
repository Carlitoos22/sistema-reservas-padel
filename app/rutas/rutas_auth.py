from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.plantillas import templates
from app.controladores import controlador_auth

router = APIRouter(tags=["Autenticacion"])


# ---------- REGISTRO ----------
@router.get("/registro", response_class=HTMLResponse)
def form_registro(request: Request):
    return templates.TemplateResponse(request, "registro.html", {})


@router.post("/registro")
def hacer_registro(
    request: Request,
    nombre: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    rol: str = Form("jugador"),
    db: Session = Depends(get_db),
):
    usuario = controlador_auth.registrar(db, nombre, email, password, rol)
    if usuario is None:
        return templates.TemplateResponse(
            request, "registro.html", {"error": "Ese email ya esta registrado."}
        )
    return RedirectResponse(url="/login", status_code=303)


# ---------- LOGIN ----------
@router.get("/login", response_class=HTMLResponse)
def form_login(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login")
def hacer_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    usuario = controlador_auth.autenticar(db, email, password)
    if usuario is None:
        return templates.TemplateResponse(
            request, "login.html", {"error": "Email o contrasena incorrectos."}
        )
    request.session["user_id"] = usuario.id
    request.session["rol"] = usuario.rol
    request.session["nombre"] = usuario.nombre
    return RedirectResponse(url="/", status_code=303)


# ---------- LOGOUT ----------
@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)