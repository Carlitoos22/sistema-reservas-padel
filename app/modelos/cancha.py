from pydantic import BaseModel, field_validator
from sqlalchemy import Column, Integer, String, Boolean
from app.validaciones import validar_texto_seguro
from app.database import Base

# ===== MODELOS: Cancha =====
# CanchaBase valida lo que llega del formulario del dueño.
# CanchaDB es la tabla "canchas" en PostgreSQL. Mantiene "nombre" y "tipo",
# que son los campos que ya usa la vista de reservas (canchas.html).


class CanchaBase(BaseModel):
    nombre: str
    tipo: str
    activa: bool = True

    @field_validator("nombre", "tipo")
    @classmethod
    def _seguro_y_no_vacio(cls, v):
        v = validar_texto_seguro(v).strip()
        if not v:
            raise ValueError("No puede estar vacío")
        if len(v) > 50:
            raise ValueError("Máximo 50 caracteres")
        return v


class CanchaDB(Base):
    __tablename__ = "canchas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)
    tipo = Column(String, nullable=False)
    activa = Column(Boolean, default=True, nullable=False)
