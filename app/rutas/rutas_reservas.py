from fastapi import APIRouter, HTTPException
from app.modelos.reserva import ReservaBase, Reserva
from app.controladores import controlador_reservas

# ===== CAPA DE RUTAS =====
# Define los endpoints (URLs) de la API para el recurso "reservas".

router = APIRouter(prefix="/api/v1/reservas", tags=["Reservas"])


# GET /api/v1/reservas  → listar todas
@router.get("")
def listar():
    return controlador_reservas.listar_reservas()


# GET /api/v1/reservas/{id}  → obtener una por id
@router.get("/{id_reserva}")
def obtener(id_reserva: int):
    reserva = controlador_reservas.obtener_reserva(id_reserva)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reserva


# POST /api/v1/reservas  → crear
@router.post("", status_code=201)
def crear(datos: ReservaBase):
    return controlador_reservas.crear_reserva(datos)


# PUT /api/v1/reservas/{id}  → actualizar
@router.put("/{id_reserva}")
def actualizar(id_reserva: int, datos: ReservaBase):
    reserva = controlador_reservas.actualizar_reserva(id_reserva, datos)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reserva


# DELETE /api/v1/reservas/{id}  → eliminar
@router.delete("/{id_reserva}", status_code=204)
def eliminar(id_reserva: int):
    borrada = controlador_reservas.eliminar_reserva(id_reserva)
    if not borrada:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return