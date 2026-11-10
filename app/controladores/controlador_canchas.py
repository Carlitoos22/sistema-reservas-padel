from sqlalchemy.orm import Session
from app.datos import repositorio_canchas, repositorio_reservas
from app.modelos.cancha import CanchaBase

# ===== CAPA DE CONTROLADORES: Canchas =====
# Reglas de negocio de la administración de canchas (rol "dueño").
# Cada operación devuelve un código de resultado que la ruta convierte en un
# mensaje en pantalla (ver MENSAJES en rutas_admin.py).

# Horarios de turno que se ofrecen en cada cancha (antes en canchas_demo.py)
HORARIOS = ["14:00 - 16:00", "16:00 - 18:00", "18:00 - 20:00", "20:00 - 22:00", "22:00 - 00:00"]

# Canchas con las que arranca una base vacía, para que la vista de reservas
# funcione desde el primer deploy. Son las mismas que tenía la lista temporal.
CANCHAS_INICIALES = [
    {"nombre": "Cancha 1", "tipo": "Cristal - techada"},
    {"nombre": "Cancha 2", "tipo": "Muro - exterior"},
    {"nombre": "Cancha 3", "tipo": "Panoramica - techada"},
]


def cargar_canchas_iniciales(db: Session):
    """Si la tabla está vacía, la completa con las canchas iniciales."""
    if repositorio_canchas.contar(db) == 0:
        for c in CANCHAS_INICIALES:
            repositorio_canchas.crear(db, c["nombre"], c["tipo"])


def listar_canchas(db: Session):
    return repositorio_canchas.listar(db)


def listar_canchas_activas(db: Session):
    """Las que ve el jugador en /canchas: una cancha desactivada no se reserva."""
    return repositorio_canchas.listar_activas(db)


def es_reservable(db: Session, nombre, hora):
    """El turno existe y la cancha está activa. Evita que se reserve, armando el
    formulario a mano, una cancha desactivada, inexistente o un horario inventado."""
    cancha = repositorio_canchas.buscar_por_nombre(db, nombre)
    return cancha is not None and cancha.activa and hora in HORARIOS


def _tiene_reservas(db: Session, nombre):
    # La reserva guarda el NOMBRE de la cancha (texto), así que se busca por nombre
    return any(r.cancha == nombre for r in repositorio_reservas.listar(db))


def crear_cancha(db: Session, datos: CanchaBase):
    if repositorio_canchas.buscar_por_nombre(db, datos.nombre):
        return "duplicada"
    repositorio_canchas.crear(db, datos.nombre, datos.tipo, datos.activa)
    return "creada"


def editar_cancha(db: Session, id_cancha, datos: CanchaBase):
    cancha = repositorio_canchas.buscar_por_id(db, id_cancha)
    if cancha is None:
        return "no_existe"

    if datos.nombre != cancha.nombre:
        otra = repositorio_canchas.buscar_por_nombre(db, datos.nombre)
        if otra and otra.id != cancha.id:
            return "duplicada"
        # Las reservas apuntan al nombre: renombrar dejaría reservas "huérfanas"
        if _tiene_reservas(db, cancha.nombre):
            return "renombre_con_reservas"

    repositorio_canchas.actualizar(db, id_cancha, {"nombre": datos.nombre, "tipo": datos.tipo})
    return "editada"


def cambiar_estado(db: Session, id_cancha):
    """Activa o desactiva la cancha. Desactivada, deja de ofrecerse para reservar
    pero conserva sus reservas (alternativa segura a eliminarla)."""
    cancha = repositorio_canchas.buscar_por_id(db, id_cancha)
    if cancha is None:
        return "no_existe"
    queda_activa = not cancha.activa
    repositorio_canchas.actualizar(db, id_cancha, {"activa": queda_activa})
    return "activada" if queda_activa else "desactivada"


def borrar_cancha(db: Session, id_cancha):
    cancha = repositorio_canchas.buscar_por_id(db, id_cancha)
    if cancha is None:
        return "no_existe"
    if _tiene_reservas(db, cancha.nombre):
        return "eliminar_con_reservas"
    repositorio_canchas.eliminar(db, id_cancha)
    return "eliminada"
