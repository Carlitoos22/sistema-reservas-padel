from sqlalchemy.orm import Session
from app.modelos.usuario import UsuarioDB


def buscar_por_email(db: Session, email: str):
    return db.query(UsuarioDB).filter(UsuarioDB.email == email).first()


def buscar_por_id(db: Session, id: int):
    return db.query(UsuarioDB).filter(UsuarioDB.id == id).first()


def crear(db: Session, nombre: str, email: str, password_hash: str, rol: str):
    nuevo = UsuarioDB(
        nombre=nombre,
        email=email,
        password_hash=password_hash,
        rol=rol,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo