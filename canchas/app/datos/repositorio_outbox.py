import json
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.datos.tablas import OutboxTabla

# ===== CAPA DE DATOS: Outbox =====


def agregar(sesion: Session, evento: dict, routing_key: str):
    """Sin commit: se confirma junto con el cambio de negocio."""
    sesion.add(OutboxTabla(
        event_id=evento["event_id"],
        tipo=evento["tipo"],
        routing_key=routing_key,
        cuerpo=json.dumps(evento, ensure_ascii=False),
        creado_en=datetime.now(),
        intentos=0,
    ))


def tomar_pendientes(sesion: Session, limite: int = 20):
    """Eventos sin publicar, en orden de creación.
    FOR UPDATE SKIP LOCKED: si hubiera dos publicadores, cada uno toma filas
    distintas en lugar de publicar dos veces las mismas."""
    consulta = (
        select(OutboxTabla)
        .where(OutboxTabla.publicado_en.is_(None))
        .order_by(OutboxTabla.id)
        .limit(limite)
        .with_for_update(skip_locked=True)
    )
    return sesion.scalars(consulta).all()


def contar_pendientes(sesion: Session) -> int:
    return len(sesion.scalars(select(OutboxTabla.id).where(OutboxTabla.publicado_en.is_(None))).all())
