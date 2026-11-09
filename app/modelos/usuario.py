from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from app.database import Base


# --- Tabla "usuarios" en la base de datos (SQLAlchemy) ---
class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    rol = Column(String, default="jugador")   # "jugador" o "dueño"


# --- Modelos de validación (Pydantic) ---
class RegistroSchema(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str = "jugador"


class LoginSchema(BaseModel):
    email: str
    password: str