from sqlalchemy import func
from sqlalchemy.orm import Session
from app.modelos.cancha import CanchaDB

# ===== CAPA DE DATOS: Canchas =====
# Único lugar que consulta la tabla "canchas" con el ORM.


def listar(db: Session):
    return db.query(CanchaDB).order_by(CanchaDB.id).all()


def listar_activas(db: Session):
    return db.query(CanchaDB).filter(CanchaDB.activa.is_(True)).order_by(CanchaDB.id).all()


def buscar_por_id(db: Session, id_cancha):
    return db.query(CanchaDB).filter(CanchaDB.id == id_cancha).first()


def buscar_por_nombre(db: Session, nombre):
    # Sin distinguir mayúsculas: "cancha 1" y "Cancha 1" son la misma cancha
    return db.query(CanchaDB).filter(func.lower(CanchaDB.nombre) == nombre.lower()).first()


def crear(db: Session, nombre, tipo, activa=True):
    cancha = CanchaDB(nombre=nombre, tipo=tipo, activa=activa)
    db.add(cancha)
    db.commit()
    db.refresh(cancha)
    return cancha


def actualizar(db: Session, id_cancha, datos):
    cancha = buscar_por_id(db, id_cancha)
    if cancha is None:
        return None
    for clave, valor in datos.items():
        setattr(cancha, clave, valor)
    db.commit()
    db.refresh(cancha)
    return cancha


def eliminar(db: Session, id_cancha):
    cancha = buscar_por_id(db, id_cancha)
    if cancha is None:
        return False
    db.delete(cancha)
    db.commit()
    return True


def contar(db: Session):
    return db.query(CanchaDB).count()
