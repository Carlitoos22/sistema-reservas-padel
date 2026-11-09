from sqlalchemy.orm import Session
from app.datos import repositorio_usuarios
from app.seguridad import hashear_password, verificar_password


def registrar(db: Session, nombre: str, email: str, password: str, rol: str):
    """Crea un usuario nuevo. Devuelve None si el email ya estaba registrado."""
    if repositorio_usuarios.buscar_por_email(db, email):
        return None
    password_hash = hashear_password(password)
    return repositorio_usuarios.crear(db, nombre, email, password_hash, rol)


def autenticar(db: Session, email: str, password: str):
    """Verifica email + contraseña. Devuelve el usuario si coincide, None si no."""
    usuario = repositorio_usuarios.buscar_por_email(db, email)
    if usuario and verificar_password(password, usuario.password_hash):
        return usuario
    return None