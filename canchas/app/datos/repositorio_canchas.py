from sqlalchemy import select
from sqlalchemy.orm import Session
from app.datos.tablas import CanchaTabla

# ===== CAPA DE DATOS: Repositorio de Canchas =====
# Única capa que habla con la base de datos del módulo.


def listar(sesion: Session, incluir_inactivas: bool = False):
    consulta = select(CanchaTabla).order_by(CanchaTabla.id)
    if not incluir_inactivas:
        consulta = consulta.where(CanchaTabla.activa.is_(True))
    return sesion.scalars(consulta).all()


def buscar_por_id(sesion: Session, id_cancha: int):
    return sesion.get(CanchaTabla, id_cancha)


def buscar_por_nombre(sesion: Session, nombre: str):
    return sesion.scalars(select(CanchaTabla).where(CanchaTabla.nombre == nombre)).first()


def crear(sesion: Session, datos: dict):
    cancha = CanchaTabla(**datos, activa=True)
    sesion.add(cancha)
    sesion.commit()
    sesion.refresh(cancha)
    return cancha


def actualizar(sesion: Session, cancha: CanchaTabla, datos: dict):
    for campo, valor in datos.items():
        setattr(cancha, campo, valor)
    sesion.commit()
    sesion.refresh(cancha)
    return cancha


def dar_de_baja(sesion: Session, cancha: CanchaTabla):
    """Baja lógica: la cancha queda guardada pero inactiva."""
    cancha.activa = False
    sesion.commit()


def buscar_por_id_para_modificar(sesion: Session, id_cancha: int):
    """Lee la cancha y la deja bloqueada (SELECT ... FOR UPDATE) hasta el commit.
    Mientras tanto, cualquier otra transacción que quiera modificar algo de esta
    misma cancha tiene que esperar: las operaciones sobre una cancha se ejecutan
    de a una."""
    return sesion.scalars(
        select(CanchaTabla).where(CanchaTabla.id == id_cancha).with_for_update()
    ).first()
