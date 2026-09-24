# ===== TOPOLOGÍA DE RABBITMQ =====
# Nombres compartidos por el consumidor y el script que simula a Reservas.
#
#   exchange "reservas" (topic)
#       ├── reserva.creada    ─┐
#       └── reserva.cancelada ─┴─► cola "canchas.reservas"  (la consume este módulo)
#                                        │ rechazo definitivo
#                                        ▼
#                  exchange "reservas.dlx" ─► cola "canchas.reservas.fallidos"
#
# Reservas publica sin saber quién escucha: si mañana otro servicio necesita
# estos eventos, crea su propia cola sobre el mismo exchange.

EXCHANGE = "reservas"
EXCHANGE_FALLIDOS = "reservas.dlx"
COLA = "canchas.reservas"
COLA_FALLIDOS = "canchas.reservas.fallidos"
CLAVES = {"ReservaCreada": "reserva.creada", "ReservaCancelada": "reserva.cancelada"}
MAX_REINTENTOS = 3


def declarar_topologia(canal):
    """Crea exchanges y colas si no existen (la operación es idempotente)."""
    canal.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
    canal.exchange_declare(EXCHANGE_FALLIDOS, exchange_type="fanout", durable=True)
    canal.queue_declare(COLA_FALLIDOS, durable=True)
    canal.queue_bind(COLA_FALLIDOS, EXCHANGE_FALLIDOS)
    canal.queue_declare(COLA, durable=True, arguments={"x-dead-letter-exchange": EXCHANGE_FALLIDOS})
    for clave in CLAVES.values():
        canal.queue_bind(COLA, EXCHANGE, routing_key=clave)


# ----- Eventos que PUBLICA este módulo -----
#
#   exchange "canchas" (topic)
#       ├── turno.bloqueado ─┐
#       └── turno.conflicto ─┴─► colas de quien quiera escuchar (Reservas)
#
# Canchas es dueño de este exchange; no crea colas de otros servicios.

EXCHANGE_CANCHAS = "canchas"
CLAVE_TURNO_BLOQUEADO = "turno.bloqueado"
CLAVE_RESERVA_EN_CONFLICTO = "turno.conflicto"


def declarar_exchange_canchas(canal):
    canal.exchange_declare(EXCHANGE_CANCHAS, exchange_type="topic", durable=True)
