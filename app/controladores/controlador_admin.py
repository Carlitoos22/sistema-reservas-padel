import os
from datetime import date
from sqlalchemy.orm import Session

from app.datos import repositorio_reservas, repositorio_usuarios
from app.controladores import controlador_canchas, controlador_auth
from app.controladores.controlador_canchas import HORARIOS

# ===== CAPA DE CONTROLADORES: Administración (rol "dueño") =====
# Resumen del día, gestión de todas las reservas y de los roles de usuario.

ROLES = ("jugador", "dueño")


# ---------- Dueño inicial ----------

def crear_dueno_inicial(db: Session):
    """El registro público solo crea jugadores. El primer dueño se define con
    variables de entorno (DUENO_EMAIL, DUENO_PASSWORD, DUENO_NOMBRE), sin
    escribir credenciales en el código. Si ese email ya existe como jugador,
    se lo promueve a dueño."""
    email = os.getenv("DUENO_EMAIL")
    password = os.getenv("DUENO_PASSWORD")
    if not email or not password:
        return None
    usuario = repositorio_usuarios.buscar_por_email(db, email)
    if usuario is None:
        nombre = os.getenv("DUENO_NOMBRE", "Dueño")
        return controlador_auth.registrar(db, nombre, email, password, "dueño")
    if usuario.rol != "dueño":
        return repositorio_usuarios.cambiar_rol(db, usuario.id, "dueño")
    return usuario


# ---------- Resumen ----------

def resumen(db: Session, fecha: str = None):
    """Números del día para el panel: canchas, turnos, ocupación y usuarios."""
    fecha = fecha or date.today().isoformat()
    activas = controlador_canchas.listar_canchas_activas(db)
    nombres_activas = {c.nombre for c in activas}
    reservas_dia = [r for r in repositorio_reservas.listar(db) if r.fecha == fecha]
    ocupados = len([r for r in reservas_dia if r.cancha in nombres_activas])
    turnos_totales = len(activas) * len(HORARIOS)
    return {
        "fecha": fecha,
        "canchas_activas": len(activas),
        "canchas_totales": len(controlador_canchas.listar_canchas(db)),
        "turnos_totales": turnos_totales,
        "turnos_ocupados": ocupados,
        "ocupacion": round(ocupados * 100 / turnos_totales) if turnos_totales else 0,
        "jugadores": repositorio_usuarios.contar_por_rol(db, "jugador"),
        "duenos": repositorio_usuarios.contar_por_rol(db, "dueño"),
        # Ocupación por cancha, para ver cuál se usa más
        "por_cancha": [
            {"nombre": c.nombre,
             "ocupados": len([r for r in reservas_dia if r.cancha == c.nombre]),
             "total": len(HORARIOS)}
            for c in activas
        ],
    }


# ---------- Reservas ----------

def listar_reservas(db: Session, fecha: str = "", cancha: str = ""):
    """Todas las reservas (de todos los jugadores), con filtros opcionales."""
    reservas = repositorio_reservas.listar(db)
    if fecha:
        reservas = [r for r in reservas if r.fecha == fecha]
    if cancha:
        reservas = [r for r in reservas if r.cancha == cancha]
    return sorted(reservas, key=lambda r: (r.fecha, r.hora, r.cancha))


def cancelar_reserva(db: Session, id_reserva):
    """El dueño puede cancelar cualquier reserva (por ejemplo, por lluvia)."""
    return "reserva_cancelada" if repositorio_reservas.eliminar(db, id_reserva) else "reserva_no_existe"


# ---------- Usuarios ----------

def listar_usuarios(db: Session):
    return repositorio_usuarios.listar(db)


def cambiar_rol(db: Session, id_usuario, rol_nuevo, quien_lo_hace):
    if rol_nuevo not in ROLES:
        return "rol_invalido"
    if id_usuario == quien_lo_hace.id:
        # Evita que el dueño se quite el rol a sí mismo y el sistema quede sin dueño
        return "rol_propio"
    usuario = repositorio_usuarios.cambiar_rol(db, id_usuario, rol_nuevo)
    if usuario is None:
        return "usuario_no_existe"
    return "rol_cambiado"
