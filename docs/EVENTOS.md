# Catálogo de eventos – Módulo de Canchas y Disponibilidad

Broker: RabbitMQ. Formato: JSON (`content_type: application/json`), mensajes persistentes (`delivery_mode: 2`).

## Topología

| Elemento | Nombre | Tipo | Dueño |
|---|---|---|---|
| Exchange | `reservas` | topic, durable | Reservas (publica) |
| Cola | `canchas.reservas` | durable, DLX `reservas.dlx` | Canchas (consume) |
| Exchange de fallidos | `reservas.dlx` | fanout, durable | Canchas |
| Cola de fallidos | `canchas.reservas.fallidos` | durable | Canchas |

## Eventos consumidos (los publica Reservas)

| Evento | Routing key | Productor | Consumidor | Efecto en Canchas |
|---|---|---|---|---|
| `ReservaCreada` | `reserva.creada` | Reservas | Canchas | El turno pasa a `ocupado` y se invalida la caché de esa fecha |
| `ReservaCancelada` | `reserva.cancelada` | Reservas | Canchas | El turno vuelve a `libre` y se invalida la caché de esa fecha |

### Contrato

```json
{
  "event_id": "7f3c2a1e-5b7d-4e8a-9c21-7d4e5f6a8b90",
  "tipo": "ReservaCreada",
  "ocurrido_en": "2026-09-30T18:42:10",
  "correlation_id": "reserva-10",
  "datos": {
    "reserva_id": 10,
    "cancha_id": 1,
    "fecha": "2026-10-01",
    "hora_inicio": "09:30:00",
    "hora_fin": "11:00:00"
  }
}
```

| Campo | Tipo | Uso |
|---|---|---|
| `event_id` | UUID | Clave de idempotencia: lo genera Reservas, uno distinto por evento |
| `tipo` | `ReservaCreada` \| `ReservaCancelada` | Qué ocurrió |
| `ocurrido_en` | ISO 8601 | Momento del hecho en Reservas |
| `correlation_id` | texto | Permite seguir una reserva en los logs de ambos servicios |
| `datos.hora_inicio` / `hora_fin` | `HH:MM:SS` | La franja que ocupa la reserva, tal como la devolvió la validación de turno |

## Garantías del consumidor

- **Entrega al menos una vez:** el `ack` se envía después del commit en la base.
- **Idempotencia:** el `event_id` se guarda en `eventos_procesados` en la misma transacción que el cambio; un evento repetido se confirma sin efecto.
- **Orden:** si `ReservaCancelada` llega antes que `ReservaCreada`, la reserva queda cancelada y la creación posterior se ignora.
- **Reintentos:** ante un error transitorio (base caída) se republica con el header `x-reintentos`, hasta 3 veces con espera de 1, 2 y 3 s.
- **Fallidos:** mensajes mal formados, eventos no aplicables (cancha inexistente) o que agotaron los reintentos van a `canchas.reservas.fallidos` para revisión manual.

## Eventos publicados (los publica Canchas)

| Evento | Exchange | Routing key | Productor | Consumidor esperado | Cuándo |
|---|---|---|---|---|---|
| `TurnoBloqueado` | `canchas` (topic, durable) | `turno.bloqueado` | Canchas (proceso `canchas-publicador`) | Reservas | Al crear un bloqueo |
| `ReservaEnConflicto` | `canchas` (topic, durable) | `turno.conflicto` | Canchas (proceso `canchas-publicador`) | Reservas | Al recibir `ReservaCreada` para una franja que ya estaba bloqueada |

### Contrato

```json
{
  "event_id": "b1e2c3d4-0000-4a5b-8c9d-112233445566",
  "tipo": "TurnoBloqueado",
  "ocurrido_en": "2026-09-30T19:05:00",
  "correlation_id": "bloqueo-3",
  "datos": {
    "bloqueo_id": 3,
    "cancha_id": 1,
    "fecha": "2026-10-01",
    "hora_desde": "14:00:00",
    "hora_hasta": "18:00:00",
    "motivo": "Mantenimiento",
    "reservas_afectadas": [21, 22]
  }
}
```

`reservas_afectadas` lista las reservas activas que se superponen con la franja bloqueada, según la ocupación que Canchas conoce por eventos. Reservas decide qué hacer con ellas (avisar al jugador, reprogramar o cancelar); Canchas no modifica reservas.

### Contrato de `ReservaEnConflicto`

```json
{
  "event_id": "5d1e...",
  "tipo": "ReservaEnConflicto",
  "ocurrido_en": "2026-09-30T19:06:10",
  "correlation_id": "reserva-30",
  "datos": {
    "reserva_id": 30,
    "cancha_id": 1,
    "fecha": "2026-10-01",
    "hora_inicio": "14:00:00",
    "hora_fin": "15:30:00",
    "bloqueos": [
      {"bloqueo_id": 3, "hora_desde": "14:00:00", "hora_hasta": "18:00:00", "motivo": "Torneo"}
    ]
  }
}
```

Entre los dos eventos, toda reserva que choca con un bloqueo se informa **exactamente una vez**: en `reservas_afectadas` de `TurnoBloqueado` si Canchas conocía la reserva al crear el bloqueo, o como `ReservaEnConflicto` si la reserva llegó después. Ver `docs/CONCURRENCIA.md`.

### Garantías del productor (patrón Transactional Outbox)

- **Atomicidad:** el bloqueo y el evento se guardan en la misma transacción (tabla `outbox`). No puede quedar un bloqueo sin evento ni un evento de un bloqueo que no se guardó.
- **Independencia del broker:** crear un bloqueo no depende de RabbitMQ. Si está caído, el evento queda pendiente en el outbox y se publica cuando vuelve.
- **Confirmación:** el publicador usa *publisher confirms*; un evento se marca como publicado solo después de que RabbitMQ confirma haberlo recibido.
- **Al menos una vez:** si el publicador se cae entre la confirmación y el marcado, el evento se vuelve a publicar. El consumidor debe deduplicar por `event_id` (también viaja como `message_id` de AMQP).
- **Orden:** los pendientes se publican en orden de creación.
- **Cola del consumidor:** Canchas es dueño del exchange, no de las colas. Cada consumidor declara su propia cola durable enlazada a `turno.*`. En este branch, `scripts/escuchar_eventos.py` simula a Reservas con la cola `simulador.reservas`.
