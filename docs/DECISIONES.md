# Decisiones de arquitectura – Módulo de Canchas y Disponibilidad

Registro de las decisiones técnicas de la AE2, con las alternativas consideradas y el motivo de la elección. La numeración coincide con la sección 2 de la Bitácora; las decisiones 9 y 10 se documentaron en la etapa 10. El proceso con el que se llegó a cada una, con fechas, está en la Bitácora.

| # | Decisión | Etapa |
|---|---|---|
| 1 | [Turno calculado, no guardado](#1-turno-calculado-no-guardado) | #4 |
| 2 | [Conocer la ocupación por eventos](#2-conocer-la-ocupación-por-eventos) | #7 |
| 3 | [Formato de la validación de turno](#3-formato-de-la-validación-de-turno) | #5 |
| 4 | [Redis como optimización, no como fuente de verdad](#4-redis-como-optimización-no-como-fuente-de-verdad) | #6 |
| 5 | [Cuándo invalidar la caché y cuánto dura](#5-cuándo-invalidar-la-caché-y-cuánto-dura) | #6 |
| 6 | [Mensajes que fallan](#6-mensajes-que-fallan) | #7 |
| 7 | [Transactional Outbox para publicar](#7-transactional-outbox-para-publicar) | #8 |
| 8 | [Lock sobre la cancha contra el write skew](#8-lock-sobre-la-cancha-contra-el-write-skew) | #9 |
| 9 | [Servicio propio con base de datos propia](#9-servicio-propio-con-base-de-datos-propia) | #1 |
| 10 | [Baja lógica de canchas](#10-baja-lógica-de-canchas) | #2 |

---

## 1. Turno calculado, no guardado

| | Guardar cada turno en una tabla | Calcular los turnos en cada consulta |
|---|---|---|
| Ventaja | Consulta directa | No hay datos redundantes; si cambia el horario, cambian todos los turnos |
| Desventaja | Miles de filas y un proceso que las genere a futuro | Hay que calcular en cada pedido |

**Decisión:** calcularlos a partir de la apertura, el cierre y la duración del turno. El costo es mínimo y lo compensa la caché de Redis. `Turno` es solo un modelo de respuesta de la API.

## 2. Conocer la ocupación por eventos

| | Consultar la API de Reservas en cada pedido | Escuchar los eventos de Reservas por RabbitMQ |
|---|---|---|
| Ventaja | Dato siempre actualizado | Desacoplamiento: si Reservas se cae, la disponibilidad se sigue mostrando |
| Desventaja | Si Reservas se cae, se cae Canchas | Consistencia eventual: puede haber un instante de desfase |

**Decisión:** eventos. El desfase no genera dobles reservas porque la verdad final sobre la ocupación la tiene el módulo de Reservas; la disponibilidad de Canchas es informativa.

**Consecuencia:** el consumidor tiene que ser idempotente, porque RabbitMQ entrega "al menos una vez". El `event_id` se guarda en `eventos_procesados` en la misma transacción que el cambio, y el `ack` se envía después del commit.

## 3. Formato de la validación de turno

| | Códigos de error HTTP (404, 409…) | Siempre 200 con `valido` y `motivo` |
|---|---|---|
| Ventaja | Más "REST puro" | El consumidor decide con un `if`; los 4xx/5xx quedan para errores reales |
| Desventaja | Mezcla "turno no disponible" con "el servicio falló" | Hay que leer el cuerpo de la respuesta |

**Decisión:** 200 con motivo codificado (`CANCHA_INEXISTENTE`, `CANCHA_INACTIVA`, `FECHA_PASADA`, `HORARIO_INVALIDO`, `TURNO_BLOQUEADO`). Para otro servicio, "el turno no es válido" es una respuesta esperable, no una falla.

## 4. Redis como optimización, no como fuente de verdad

| | Fallar con 500 si Redis no responde | Calcular desde PostgreSQL y registrar un aviso |
|---|---|---|
| Ventaja | Se nota enseguida que Redis está caído | La disponibilidad sigue funcionando |
| Desventaja | Una dependencia secundaria tira abajo una funcionalidad principal | Más carga sobre la base mientras Redis esté caído |

**Decisión:** degradar a PostgreSQL. La caída de Redis se ve en `/health` (503 degradado) y en el log.

## 5. Cuándo invalidar la caché y cuánto dura

| | Invalidar antes del commit | Invalidar después del commit |
|---|---|---|
| Riesgo | Una consulta que llega en el medio vuelve a cachear el dato sin el cambio | Carrera más chica: una consulta que leyó antes del commit puede guardar el dato viejo después de la invalidación |

**Decisión:** invalidar después del commit, con un TTL de 300 s como red de seguridad. La carrera residual no se puede eliminar del todo con cache-aside, pero el TTL la acota a 5 minutos. Tampoco genera reservas inválidas: la validación de turno siempre consulta la base, así que un turno bloqueado nunca se valida aunque la grilla lo muestre libre un rato.

Granularidad: un bloqueo o un evento de reserva invalida solo esa cancha y esa fecha; un cambio en la cancha invalida todas sus fechas.

## 6. Mensajes que fallan

| | Reencolar siempre | Reintentar solo errores transitorios y mandar el resto a una cola de fallidos |
|---|---|---|
| Ventaja | Simple | Un mensaje roto no bloquea la cola ni se reintenta para siempre |
| Desventaja | Un mensaje mal formado se reintenta en bucle infinito ("mensaje veneno") | Hay que clasificar los errores |

**Decisión:** la segunda. Un error transitorio (base caída) se reintenta hasta 3 veces con espera creciente; un mensaje mal formado o de una cancha inexistente va directo a `canchas.reservas.fallidos`. El reintento se republica solo a la cola de Canchas, no al exchange, para no duplicarles el mensaje a otros servicios.

## 7. Transactional Outbox para publicar

**Contexto.** Crear un bloqueo implica escribir en PostgreSQL y publicar `TurnoBloqueado` en RabbitMQ, y no hay una transacción que abarque a los dos.

| | Commit y después publicar | Publicar y después commit | Transactional Outbox |
|---|---|---|---|
| Si RabbitMQ falla | Bloqueo guardado, **evento perdido** | — | El evento queda en la tabla y sale después |
| Si la base falla | — | **Evento de un bloqueo que no existe** | No se guarda ni el bloqueo ni el evento |
| Costo | Ninguno | Ninguno | Una tabla y un proceso publicador |

**Decisión:** outbox, con un proceso aparte (`canchas-publicador`) que publica con *publisher confirms*. Crear un bloqueo no depende de RabbitMQ.

**Consecuencia:** la entrega es "al menos una vez": si el publicador se cae entre la confirmación y el marcado, el evento se publica de nuevo. Por eso cada evento lleva `event_id` (también como `message_id` de AMQP), para que el consumidor deduplique igual que Canchas en la decisión 2.

## 8. Lock sobre la cancha contra el write skew

**Contexto.** Un bloqueo y una reserva de la misma franja procesados al mismo tiempo pueden terminar sin que ninguno informe el choque. El análisis completo está en [`CONCURRENCIA.md`](CONCURRENCIA.md).

| | Aislamiento SERIALIZABLE | Lock en Redis | `SELECT ... FOR UPDATE` sobre la cancha |
|---|---|---|---|
| Ventaja | Lo detecta el motor sin cambiar la lógica | Sirve entre procesos distintos | Predecible; reusa el lock que ya existía desde la etapa 3 |
| Desventaja | Aborta una transacción y obliga a reintentar; en el consumidor genera reintentos de mensajes y en la API errores | Una dependencia más, y no es transaccional con PostgreSQL: el lock puede vencer antes del commit | Serializa las escrituras sobre una misma cancha |

**Decisión:** lock sobre la fila de la cancha. En un complejo de pádel las escrituras sobre una misma cancha son pocas por minuto, las canchas distintas no se bloquean entre sí y las consultas de disponibilidad no toman el lock.

También se descartó que Canchas rechace la reserva: Canchas no es dueño de las reservas. Informa el choque (`reservas_afectadas` o `ReservaEnConflicto`) y Reservas decide qué hacer con el jugador.

## 9. Servicio propio con base de datos propia

**Contexto.** En el AE1 todo era una sola aplicación con un archivo JSON. La consigna de la AE2 prohíbe que un servicio consulte directamente las tablas de otro.

| | Compartir la base con Reservas | Base propia (PostgreSQL) |
|---|---|---|
| Ventaja | Un solo motor; se puede hacer un JOIN con las reservas | Cada módulo evoluciona su esquema sin romper al otro; no hay lecturas cruzadas |
| Desventaja | Acoplamiento por esquema: un cambio en la tabla de reservas rompe a Canchas | Lo que Canchas necesita de Reservas tiene que llegar por API o por eventos |

**Decisión:** base propia, en su propio contenedor (`canchas-db`). El código vive en `canchas/`, separado de `app/` (Reservas), para que el merge de la AE4 no genere conflictos.

**Consecuencia:** la ocupación de turnos se conoce por eventos (decisión 2).

## 10. Baja lógica de canchas

| | DELETE físico | Marcar `activa = false` |
|---|---|---|
| Ventaja | Simple | Las reservas históricas siguen apuntando a una cancha que existe |
| Desventaja | Deja reservas pasadas apuntando a un id inexistente, en otro servicio que no se entera | Hay que filtrar las inactivas en los listados |

**Decisión:** baja lógica. `GET /canchas` excluye las inactivas salvo con `incluir_inactivas=true`, y una cancha inactiva no acepta bloqueos ni valida turnos (`CANCHA_INACTIVA`).
