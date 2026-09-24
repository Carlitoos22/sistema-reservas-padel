# Catálogo de eventos – Módulo de Canchas y Disponibilidad

Broker: RabbitMQ. Formato: JSON (`content_type: application/json`), mensajes persistentes (`delivery_mode: 2`).

## Topología

| Elemento | Nombre | Tipo | Dueño |
|---|---|---|---|
| Exchange | `reservas` | topic, durable | Reservas (publica) |
| Cola | `canchas.reservas` | durable, DLX `reservas.dlx` | Canchas (consume) |
| Exchange de fallidos | `reservas.dlx` | fanout, durable | Canchas |
| Cola de fallidos | `canchas.reservas.fallidos` | durable | Canchas |

## Eventos consumidos

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
