from datetime import date

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.plantillas import templates
from app.seguridad import requerir_dueno
from app.controladores import controlador_canchas, controlador_admin
from app.modelos.cancha import CanchaBase

# ===== RUTAS DE ADMINISTRACIÓN (solo rol "dueño") =====
# TODAS dependen de requerir_dueno: sin sesión -> va al login,
# si es jugador -> página de acceso denegado (403). Ver main.py.

router = APIRouter(prefix="/admin", tags=["Administración"])

# Código de resultado -> (texto, tipo de aviso). Por la URL viaja un código,
# nunca un texto libre, para no reflejar contenido del usuario en la página.
MENSAJES = {
    # Canchas
    "creada": ("Cancha creada.", "ok"),
    "editada": ("Cambios guardados.", "ok"),
    "activada": ("La cancha vuelve a estar disponible para reservar.", "ok"),
    "desactivada": ("La cancha quedó desactivada: los jugadores ya no la ven.", "ok"),
    "eliminada": ("Cancha eliminada.", "ok"),
    "duplicada": ("Ya existe una cancha con ese nombre.", "busy"),
    "invalida": ("Datos inválidos: el nombre y el tipo no pueden estar vacíos ni tener caracteres como < > ' \" ;", "busy"),
    "no_existe": ("Esa cancha no existe.", "busy"),
    "eliminar_con_reservas": ("No se puede eliminar: la cancha tiene reservas. Desactivala para que no se reserve más.", "busy"),
    "renombre_con_reservas": ("No se puede cambiar el nombre: la cancha tiene reservas. Podés cambiar el tipo.", "busy"),
    # Reservas
    "reserva_cancelada": ("Reserva cancelada. El turno quedó libre.", "ok"),
    "reserva_no_existe": ("Esa reserva ya no existe.", "busy"),
    # Usuarios
    "rol_cambiado": ("Rol actualizado.", "ok"),
    "rol_propio": ("No podés cambiar tu propio rol: el sistema podría quedarse sin dueño.", "busy"),
    "rol_invalido": ("Rol inválido.", "busy"),
    "usuario_no_existe": ("Ese usuario no existe.", "busy"),
}


def _mensaje(msg):
    texto, tipo = MENSAJES.get(msg, (None, None))
    return {"mensaje": texto, "tipo_mensaje": tipo}


def _volver(pagina, codigo):
    return RedirectResponse(url=f"/admin/{pagina}?msg={codigo}", status_code=303)


def _validar_cancha(nombre, tipo):
    try:
        return CanchaBase(nombre=nombre, tipo=tipo)
    except ValidationError:
        return None


def _fecha_valida(fecha):
    try:
        return date.fromisoformat(fecha).isoformat() if fecha else ""
    except ValueError:
        return ""


# ---------- Resumen ----------

@router.get("", response_class=HTMLResponse)
def resumen(request: Request, fecha: str = "", usuario=Depends(requerir_dueno),
            db: Session = Depends(get_db)):
    datos = controlador_admin.resumen(db, _fecha_valida(fecha) or None)
    return templates.TemplateResponse(
        request, "admin_resumen.html",
        {"usuario": usuario, "seccion": "resumen", "r": datos},
    )


# ---------- Canchas ----------

@router.get("/canchas", response_class=HTMLResponse)
def panel_canchas(request: Request, msg: str = "", usuario=Depends(requerir_dueno),
                  db: Session = Depends(get_db)):
    canchas = controlador_canchas.listar_canchas(db)
    return templates.TemplateResponse(
        request, "admin_canchas.html",
        {"usuario": usuario, "seccion": "canchas", "canchas": canchas, **_mensaje(msg)},
    )


@router.post("/canchas/crear")
def crear_cancha(request: Request, nombre: str = Form(...), tipo: str = Form(...),
                 usuario=Depends(requerir_dueno), db: Session = Depends(get_db)):
    datos = _validar_cancha(nombre, tipo)
    if datos is None:
        return _volver("canchas", "invalida")
    return _volver("canchas", controlador_canchas.crear_cancha(db, datos))


@router.post("/canchas/{id_cancha}/editar")
def editar_cancha(request: Request, id_cancha: int, nombre: str = Form(...), tipo: str = Form(...),
                  usuario=Depends(requerir_dueno), db: Session = Depends(get_db)):
    datos = _validar_cancha(nombre, tipo)
    if datos is None:
        return _volver("canchas", "invalida")
    return _volver("canchas", controlador_canchas.editar_cancha(db, id_cancha, datos))


@router.post("/canchas/{id_cancha}/estado")
def cambiar_estado_cancha(request: Request, id_cancha: int,
                          usuario=Depends(requerir_dueno), db: Session = Depends(get_db)):
    return _volver("canchas", controlador_canchas.cambiar_estado(db, id_cancha))


@router.post("/canchas/{id_cancha}/eliminar")
def eliminar_cancha(request: Request, id_cancha: int,
                    usuario=Depends(requerir_dueno), db: Session = Depends(get_db)):
    return _volver("canchas", controlador_canchas.borrar_cancha(db, id_cancha))


# ---------- Reservas ----------

@router.get("/reservas", response_class=HTMLResponse)
def panel_reservas(request: Request, fecha: str = "", cancha: str = "", msg: str = "",
                   usuario=Depends(requerir_dueno), db: Session = Depends(get_db)):
    fecha = _fecha_valida(fecha)
    reservas = controlador_admin.listar_reservas(db, fecha, cancha)
    return templates.TemplateResponse(
        request, "admin_reservas.html",
        {"usuario": usuario, "seccion": "reservas", "reservas": reservas,
         "canchas": controlador_canchas.listar_canchas(db),
         "fecha": fecha, "cancha": cancha, **_mensaje(msg)},
    )


@router.post("/reservas/{id_reserva}/cancelar")
def cancelar_reserva(request: Request, id_reserva: int,
                     usuario=Depends(requerir_dueno), db: Session = Depends(get_db)):
    return _volver("reservas", controlador_admin.cancelar_reserva(db, id_reserva))


# ---------- Usuarios ----------

@router.get("/usuarios", response_class=HTMLResponse)
def panel_usuarios(request: Request, msg: str = "", usuario=Depends(requerir_dueno),
                   db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "admin_usuarios.html",
        {"usuario": usuario, "seccion": "usuarios",
         "usuarios": controlador_admin.listar_usuarios(db), **_mensaje(msg)},
    )


@router.post("/usuarios/{id_usuario}/rol")
def cambiar_rol(request: Request, id_usuario: int, rol: str = Form(...),
                usuario=Depends(requerir_dueno), db: Session = Depends(get_db)):
    return _volver("usuarios", controlador_admin.cambiar_rol(db, id_usuario, rol, usuario))
