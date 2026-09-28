from sqlalchemy.orm import Session
from app.datos import repositorio_reservas
from app.modelos.reserva import ReservaBase

# ===== CAPA DE CONTROLADORES =====
# Coordina las operaciones. Ahora recibe la sesión (db) y se la pasa al repositorio.

def listar_reservas(db: Session):
    return repositorio_reservas.listar(db)


def obtener_reserva(db: Session, id_reserva):
    return repositorio_reservas.buscar_por_id(db, id_reserva)


def crear_reserva(db: Session, datos: ReservaBase):
    nueva = datos.model_dump()
    return repositorio_reservas.crear(db, nueva)


def actualizar_reserva(db: Session, id_reserva, datos: ReservaBase):
    datos_nuevos = datos.model_dump()
    return repositorio_reservas.actualizar(db, id_reserva, datos_nuevos)


def eliminar_reserva(db: Session, id_reserva):
    return repositorio_reservas.eliminar(db, id_reserva)