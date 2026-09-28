from sqlalchemy.orm import Session
from app.modelos.reserva import ReservaDB

# ===== CAPA DE DATOS: Repositorio de Reservas (PostgreSQL) =====
# Ahora usa SQLAlchemy (el ORM) para leer y escribir en la base.
# Cada función recibe una "sesión" (db) para hablar con PostgreSQL.


def listar(db: Session):
    """Devuelve todas las reservas."""
    return db.query(ReservaDB).all()


def buscar_por_id(db: Session, id_reserva):
    """Busca una reserva por su id. Devuelve la reserva o None."""
    return db.query(ReservaDB).filter(ReservaDB.id == id_reserva).first()


def crear(db: Session, datos_reserva):
    """Crea una nueva reserva y la guarda."""
    nueva = ReservaDB(**datos_reserva)   # crea el objeto de la tabla
    db.add(nueva)                        # lo agrega a la sesión
    db.commit()                          # confirma (guarda en la base)
    db.refresh(nueva)                    # trae el id que asignó Postgres
    return nueva


def actualizar(db: Session, id_reserva, datos_nuevos):
    """Actualiza una reserva existente. Devuelve la reserva o None."""
    reserva = db.query(ReservaDB).filter(ReservaDB.id == id_reserva).first()
    if reserva is None:
        return None
    for clave, valor in datos_nuevos.items():
        setattr(reserva, clave, valor)   # actualiza cada campo
    db.commit()
    db.refresh(reserva)
    return reserva


def eliminar(db: Session, id_reserva):
    """Elimina una reserva. Devuelve True si la borró, False si no existía."""
    reserva = db.query(ReservaDB).filter(ReservaDB.id == id_reserva).first()
    if reserva is None:
        return False
    db.delete(reserva)
    db.commit()
    return True