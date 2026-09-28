from dotenv import load_dotenv
import os
from app.database import engine, Base
from app.modelos import reserva

load_dotenv()   # carga las variables del archivo .env
from fastapi import FastAPI
from app.rutas import rutas_reservas
from app.errores.manejador_errores import manejador_errores_general

# ===== PUNTO DE ENTRADA DE LA APLICACIÓN =====
# Crea la app de FastAPI y conecta las rutas.

app = FastAPI(
    title=os.getenv("NOMBRE_APP", "API de Reservas"),
    description="Hito 1 (AE1) - CRUD de Reservas",
    version="1.0.0"
)

# Crea las tablas en la base de datos si no existen
Base.metadata.create_all(bind=engine)

# Conectamos las rutas de reservas a la aplicación
app.include_router(rutas_reservas.router)
app.add_exception_handler(Exception, manejador_errores_general)


# Ruta raíz, solo para verificar que la API está viva
@app.get("/")
def inicio():
    return {"mensaje": "API de Reservas de Pádel funcionando"}
