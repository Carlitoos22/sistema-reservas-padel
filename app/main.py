from dotenv import load_dotenv
import os

from app.database import engine, Base, get_db
from app.modelos import reserva
from app.modelos import usuario            # para que se cree la tabla "usuarios"

load_dotenv()      # carga las variables del archivo .env

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from app.rutas import rutas_reservas
from app.rutas import rutas_auth
from app.rutas import rutas_web
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

# Rutas
app.include_router(rutas_auth.router)
app.include_router(rutas_reservas.router)
app.include_router(rutas_web.router)

app.add_exception_handler(Exception, manejador_errores_general)


@app.get("/", response_class=HTMLResponse)
def inicio(request: Request, db: Session = Depends(get_db)):
    usuario_logueado = usuario_actual(request, db)
    return templates.TemplateResponse(
        request, "home.html", {"usuario": usuario_logueado}
    )

@app.get("/health")
def health():
    return {"status": "ok"}