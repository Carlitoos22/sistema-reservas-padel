from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.modelos.reserva import ReservaBase, Reserva
from app.controladores import controlador_reservas
from app.database import get_db
from fastapi import APIRouter, HTTPException, Depends, Header

# ===== CAPA DE RUTAS =====
# Cada endpoint obtiene una sesión de base de datos con Depends(get_db)
# y se la pasa al controlador.

router = APIRouter(prefix="/api/v1/reservas", tags=["Reservas"])


# GET /api/v1/reservas  → listar todas
@router.get("")
def listar(db: Session = Depends(get_db)):
    return controlador_reservas.listar_reservas(db)


# GET /api/v1/reservas/{id}  → obtener una por id
@router.get("/{id_reserva}")
def obtener(id_reserva: int, db: Session = Depends(get_db)):
    reserva = controlador_reservas.obtener_reserva(db, id_reserva)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reserva


# POST /api/v1/reservas  → crear
@router.post("", status_code=201)
def crear(
    datos: ReservaBase,
    db: Session = Depends(get_db),
    idempotency_key: str = Header(default=None)
):
    return controlador_reservas.crear_reserva(db, datos, idempotency_key)

# PUT /api/v1/reservas/{id}  → actualizar
@router.put("/{id_reserva}")
def actualizar(id_reserva: int, datos: ReservaBase, db: Session = Depends(get_db)):
    reserva = controlador_reservas.actualizar_reserva(db, id_reserva, datos)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reserva


# DELETE /api/v1/reservas/{id}  → eliminar
@router.delete("/{id_reserva}", status_code=204)
def eliminar(id_reserva: int, db: Session = Depends(get_db)):
    borrada = controlador_reservas.eliminar_reserva(db, id_reserva)
    if not borrada:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return