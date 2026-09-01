import json
import os

# ===== CAPA DE DATOS: Repositorio de Reservas =====
# Se encarga de leer y guardar las reservas en un archivo JSON.
# Es la única capa que "toca" el almacenamiento.

RUTA_ARCHIVO = "reservas.json"


def _leer_todas():
    """Lee todas las reservas del archivo JSON."""
    # Si el archivo no existe todavía, devolvemos una lista vacía
    if not os.path.exists(RUTA_ARCHIVO):
        return []
    with open(RUTA_ARCHIVO, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar_todas(reservas):
    """Guarda la lista completa de reservas en el archivo JSON."""
    with open(RUTA_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(reservas, f, indent=4, ensure_ascii=False)



# ===== FUNCIONES DEL CRUD =====

def listar():
    """Devuelve todas las reservas."""
    return _leer_todas()


def buscar_por_id(id_reserva):
    """Busca una reserva por su id. Devuelve la reserva o None si no existe."""
    reservas = _leer_todas()
    for reserva in reservas:
        if reserva["id"] == id_reserva:
            return reserva
    return None


def crear(datos_reserva):
    """Crea una nueva reserva, le asigna un id y la guarda."""
    reservas = _leer_todas()

    # Calculamos el nuevo id: el mayor id existente + 1 (o 1 si está vacío)
    if reservas:
        nuevo_id = max(r["id"] for r in reservas) + 1
    else:
        nuevo_id = 1

    datos_reserva["id"] = nuevo_id
    reservas.append(datos_reserva)
    _guardar_todas(reservas)
    return datos_reserva


def actualizar(id_reserva, datos_nuevos):
    """Actualiza una reserva existente. Devuelve la reserva o None si no existe."""
    reservas = _leer_todas()
    for i, reserva in enumerate(reservas):
        if reserva["id"] == id_reserva:
            datos_nuevos["id"] = id_reserva      # mantenemos el id original
            reservas[i] = datos_nuevos
            _guardar_todas(reservas)
            return datos_nuevos
    return None


def eliminar(id_reserva):
    """Elimina una reserva por su id. Devuelve True si la borró, False si no existía."""
    reservas = _leer_todas()
    for i, reserva in enumerate(reservas):
        if reserva["id"] == id_reserva:
            reservas.pop(i)
            _guardar_todas(reservas)
            return True
    return False