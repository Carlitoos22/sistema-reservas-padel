from passlib.context import CryptContext
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.modelos.usuario import UsuarioDB

# Cifra las contraseñas con pbkdf2_sha256 (no necesita librerías externas de C)
contexto_password = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hashear_password(password: str) -> str:
    """Convierte la contraseña en texto plano a un hash que se guarda en la base."""
    return contexto_password.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    """Compara la contraseña escrita con el hash guardado."""
    return contexto_password.verify(password, password_hash)


def usuario_actual(request: Request, db: Session = Depends(get_db)):
    """Devuelve el usuario logueado (según la cookie) o None si no hay nadie."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(UsuarioDB).filter(UsuarioDB.id == user_id).first()


def requerir_login(request: Request, db: Session = Depends(get_db)):
    """Igual que usuario_actual, pero corta con 401 si no hay sesión iniciada."""
    usuario = usuario_actual(request, db)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Tenés que iniciar sesión.")
    return usuario


def requerir_dueno(usuario: UsuarioDB = Depends(requerir_login)):
    """Solo deja pasar si el usuario logueado tiene rol 'dueño'."""
    if usuario.rol != "dueño":
        raise HTTPException(status_code=403, detail="Solo el dueño puede hacer esto.")
    return usuario