import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app import cache
from app.datos import repositorio_ocupaciones as repo, repositorio_canchas, repositorio_bloqueos
from app.controladores.eventos_canchas import registrar_reserva_en_conflicto
from app.modelos.evento import EventoReserva, TipoEvento

# ===== CAPA DE CONTROLADORES: Ocupación (RF-C5) =====
# Aplica los eventos ReservaCreada / ReservaCancelada sobre la ocupación local.
# No sabe nada de RabbitMQ: recibe un evento ya validado y devuelve el resultado,
# así se puede probar sin el broker.
#
# Garantías:
# - Idempotencia: el event_id se guarda en la misma transacción que el cambio.
#   Si el evento llega dos veces (RabbitMQ entrega "al menos una vez"), el
#   segundo no tiene efecto.
# - Orden: si la cancelación llega antes que la creación, se guarda la
#   ocupación ya cancelada; cuando llega la creación, se ignora. Una reserva
#   cancelada nunca vuelve a quedar activa.

log = logging.getLogger("canchas.ocupacion")

PROCESADO = "procesado"
DUPLICADO = "duplicado"


class EventoInvalido(Exception):
    """El evento está bien formado pero no se puede aplicar (p. ej. cancha inexistente).
    Reintentar no lo arregla: va a la cola de fallidos."""


def procesar_evento(sesion: Session, evento: EventoReserva) -> str:
    event_id = str(evento.event_id)
    d = evento.datos

    if repo.evento_ya_procesado(sesion, event_id):
        log.info("Evento %s duplicado, se descarta [correlation_id=%s]", event_id, evento.correlation_id)
        return DUPLICADO

    # Lock sobre la cancha (SELECT ... FOR UPDATE), el MISMO que toma la
    # creación de bloqueos. Sin él hay una carrera (write skew): el bloqueo lee
    # las ocupaciones sin ver esta reserva, esta transacción lee los bloqueos
    # sin ver ese bloqueo, las dos confirman y la reserva en conflicto no se
    # informa por ningún lado. Con el lock, la segunda espera a la primera y,
    # al continuar, ve lo que la primera confirmó.
    if repositorio_canchas.buscar_por_id_para_modificar(sesion, d.cancha_id) is None:
        raise EventoInvalido(f"la cancha {d.cancha_id} no existe")

    ocupacion = repo.buscar_por_reserva(sesion, d.reserva_id)
    datos = d.model_dump()

    if evento.tipo == TipoEvento.reserva_creada:
        if ocupacion is None:
            repo.agregar(sesion, datos, activa=True)
            # La reserva existe en Reservas aunque choque con un bloqueo: se
            # registra igual y se avisa del conflicto para que Reservas actúe.
            bloqueos = repositorio_bloqueos.buscar_superpuestos(
                sesion, d.cancha_id, d.fecha, d.hora_inicio, d.hora_fin)
            if bloqueos:
                registrar_reserva_en_conflicto(sesion, d, bloqueos, evento.correlation_id)
                log.warning("Reserva %s en conflicto con bloqueo(s) %s [correlation_id=%s]",
                            d.reserva_id, [b.id for b in bloqueos], evento.correlation_id)
        elif not ocupacion.activa:
            log.info("ReservaCreada de la reserva %s llegó después de su cancelación; se ignora", d.reserva_id)
    else:  # ReservaCancelada
        if ocupacion is None:
            # Llegó antes que la creación: se deja registrada como cancelada.
            repo.agregar(sesion, datos, activa=False)
        else:
            ocupacion.activa = False

    repo.registrar_evento(sesion, event_id, evento.tipo.value)
    try:
        sesion.commit()
    except IntegrityError:
        # Otro consumidor guardó el mismo evento entre el chequeo y el commit.
        sesion.rollback()
        if repo.evento_ya_procesado(sesion, event_id):
            return DUPLICADO
        raise

    # Después del commit, igual que con los bloqueos.
    cache.invalidar_fecha(d.cancha_id, d.fecha)
    log.info("Evento %s %s aplicado a la reserva %s [correlation_id=%s]",
             evento.tipo.value, event_id, d.reserva_id, evento.correlation_id)
    return PROCESADO
