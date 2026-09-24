import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.datos import repositorio_outbox, repositorio_ocupaciones
from app.mensajeria import CLAVE_TURNO_BLOQUEADO

# ===== Construcción de los eventos que publica Canchas =====


def registrar_turno_bloqueado(sesion: Session, bloqueo):
    """Deja TurnoBloqueado en el outbox (sin commit).

    Incluye las reservas que ya ocupaban esa franja: Canchas las conoce por
    los eventos de Reservas, y así Reservas puede avisar o reprogramar a esos
    jugadores sin tener que consultar nada."""
    afectadas = [
        o.reserva_id
        for o in repositorio_ocupaciones.listar_activas(sesion, bloqueo.cancha_id, bloqueo.fecha)
        if bloqueo.hora_desde < o.hora_fin and o.hora_inicio < bloqueo.hora_hasta  # se superponen
    ]
    evento = {
        "event_id": str(uuid.uuid4()),
        "tipo": "TurnoBloqueado",
        "ocurrido_en": datetime.now().isoformat(),
        "correlation_id": f"bloqueo-{bloqueo.id}",
        "datos": {
            "bloqueo_id": bloqueo.id,
            "cancha_id": bloqueo.cancha_id,
            "fecha": bloqueo.fecha.isoformat(),
            "hora_desde": bloqueo.hora_desde.isoformat(),
            "hora_hasta": bloqueo.hora_hasta.isoformat(),
            "motivo": bloqueo.motivo,
            "reservas_afectadas": sorted(afectadas),
        },
    }
    repositorio_outbox.agregar(sesion, evento, CLAVE_TURNO_BLOQUEADO)
    return evento
