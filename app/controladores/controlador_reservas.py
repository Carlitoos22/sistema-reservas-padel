from app.datos import repositorio_reservas
from app.modelos.reserva import ReservaBase

# ===== CAPA DE CONTROLADORES =====
# Coordina las operaciones: recibe la petición desde las rutas,
# usa el repositorio (capa de datos) y devuelve el resultado.

def listar_reservas():
    """Devuelve todas las reservas."""
    return repositorio_reservas.listar()


def obtener_reserva(id_reserva):
    """Devuelve una reserva por id (o None si no existe)."""
    return repositorio_reservas.buscar_por_id(id_reserva)


def crear_reserva(datos: ReservaBase):
    """Crea una nueva reserva."""
    # Convertimos el modelo de Pydantic a un diccionario común
    nueva = datos.model_dump()
    return repositorio_reservas.crear(nueva)


def actualizar_reserva(id_reserva, datos: ReservaBase):
    """Actualiza una reserva existente (o None si no existe)."""
    datos_nuevos = datos.model_dump()
    return repositorio_reservas.actualizar(id_reserva, datos_nuevos)


def eliminar_reserva(id_reserva):
    """Elimina una reserva. Devuelve True/False."""
    return repositorio_reservas.eliminar(id_reserva)