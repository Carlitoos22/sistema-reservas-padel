from dotenv import load_dotenv
import os

from app.database import engine, Base, get_db
from app.modelos import reserva
from app.modelos import usuario            # para que se cree la tabla "usuarios"
from app.modelos import cancha             # para que se cree la tabla "canchas"

load_dotenv()      # carga las variables del archivo .env

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from app.rutas import rutas_reservas
from app.rutas import rutas_auth
from app.rutas import rutas_web
from app.rutas import rutas_admin
from app.rutas import rutas_comprobante
from app.database import SessionLocal
from app.controladores import controlador_canchas, controlador_admin
from fastapi.responses import RedirectResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.errores.manejador_errores import manejador_errores_general
from app.seguridad_http import aplicar_seguridad_http
from app.seguridad import usuario_actual
from app.plantillas import templates

# ===== PUNTO DE ENTRADA DE LA APLICACION =====
app = FastAPI(
    title=os.getenv("NOMBRE_APP", "API de Reservas"),
    description="AE4 - Integracion final (API + Login + Frontend)",
    version="4.0.0"
)

# Headers de seguridad + error 400 (Unidad 4)
aplicar_seguridad_http(app)

# Cookie de sesion (para recordar quien esta logueado)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("CLAVE_SECRETA", "cambiar-esta-clave-en-produccion"),
)

# Archivos estaticos (CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Crea las tablas si no existen (reservas y usuarios)
Base.metadata.create_all(bind=engine)

# Si la tabla de canchas está vacía (primer deploy), carga las canchas iniciales
# y crea el dueño inicial definido por variables de entorno (DUENO_EMAIL, DUENO_PASSWORD)
with SessionLocal() as db_inicial:
    controlador_canchas.cargar_canchas_iniciales(db_inicial)
    controlador_admin.crear_dueno_inicial(db_inicial)

# Rutas
app.include_router(rutas_auth.router)
app.include_router(rutas_reservas.router)
app.include_router(rutas_web.router)
app.include_router(rutas_admin.router)
app.include_router(rutas_comprobante.router)

app.add_exception_handler(Exception, manejador_errores_general)


@app.exception_handler(StarletteHTTPException)
async def acceso_admin(request: Request, exc: StarletteHTTPException):
    """En las páginas de administración, un 401 manda al login y un 403 muestra
    una página de acceso denegado, en vez de un JSON. La API sigue igual."""
    if request.url.path.startswith("/admin"):
        if exc.status_code == 401:
            return RedirectResponse(url="/login", status_code=303)
        if exc.status_code == 403:
            return templates.TemplateResponse(request, "acceso_denegado.html", {}, status_code=403)
    return await http_exception_handler(request, exc)


@app.get("/", response_class=HTMLResponse)
def inicio(request: Request, db: Session = Depends(get_db)):
    usuario_logueado = usuario_actual(request, db)
    return templates.TemplateResponse(
        request, "home.html", {"usuario": usuario_logueado}
    )

@app.get("/health")
def health():
    return {"status": "ok"}