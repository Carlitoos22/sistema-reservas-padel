from sqlalchemy.orm import Session
from app.datos import repositorio_reservas
from app.modelos.reserva import ReservaBase
from app.redis_client import redis_client
from fastapi import HTTPException
from app.rabbitmq_client import publicar_reserva_confirmada

# ===== CAPA DE CONTROLADORES =====
# Coordina las operaciones. Ahora recibe la sesión (db) y se la pasa al repositorio.

def listar_reservas(db: Session):
    return repositorio_reservas.listar(db)


def obtener_reserva(db: Session, id_reserva):
    return repositorio_reservas.buscar_por_id(db, id_reserva)


def crear_reserva(db: Session, datos: ReservaBase, idempotency_key: str = None):
    # ===== RF-B: IDEMPOTENCIA =====
    # Si vino una clave de idempotencia y ya la procesamos antes,
    # devolvemos el id guardado en vez de crear una reserva nueva.
    if idempotency_key:
        clave_redis = f"idempotency:{idempotency_key}"
        id_existente = redis_client.get(clave_redis)
        if id_existente:
            # Ya se procesó esta petición: devolvemos la reserva original
            reserva = repositorio_reservas.buscar_por_id(db, int(id_existente))
            if reserva:
                return reserva

    # Armamos la llave del turno (cancha + fecha + hora)
    llave_turno = f"turno:{datos.cancha}:{datos.fecha}:{datos.hora}"

    # ===== RF-A: BLOQUEO DE CONCURRENCIA =====
    candado = redis_client.set(llave_turno, "ocupado", nx=True, ex=10)
    if not candado:
        raise HTTPException(
            status_code=409,
            detail="Ese turno está siendo reservado por otro jugador. Intentá de nuevo."
        )

    try:
        # Verificamos que el turno no esté ya reservado en la base
        reservas = repositorio_reservas.listar(db)
        for r in reservas:
            if r.cancha == datos.cancha and r.fecha == datos.fecha and r.hora == datos.hora:
                raise HTTPException(status_code=409, detail="Ese turno ya está reservado.")

        # Creamos la reserva
        nueva = datos.model_dump()
        reserva_creada = repositorio_reservas.crear(db, nueva)

        # Guardamos la clave de idempotencia con el id creado (TTL 1 hora)
        if idempotency_key:
            redis_client.set(f"idempotency:{idempotency_key}", reserva_creada.id, ex=3600)

        # ===== RF-C: PUBLICAR EVENTO ASÍNCRONO =====
        publicar_reserva_confirmada(reserva_creada)

        return reserva_creada
    finally:
        redis_client.delete(llave_turno)


def actualizar_reserva(db: Session, id_reserva, datos: ReservaBase):
    datos_nuevos = datos.model_dump()
    return repositorio_reservas.actualizar(db, id_reserva, datos_nuevos)


def eliminar_reserva(db: Session, id_reserva):
    return repositorio_reservas.eliminar(db, id_reserva)