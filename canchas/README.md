# Servicio de Canchas y Disponibilidad (AE2)

Módulo individual de la AE2 de Paradigmas y Lenguajes de Programación III (UCP, 2026).

- **Estudiante:** Salazar, Juan Martín
- **Branch:** `ae2/juan-salazar`
- **Versión base del AE1:** tag `v1.0-ae1` (commit `b8204f0` de `main`, CRUD de reservas en archivo JSON)
- **Alcance comprometido:** [`docs/ALCANCE_AE2_canchas.md`](../docs/ALCANCE_AE2_canchas.md)

En el AE1 la cancha era un texto libre dentro de la reserva (`"cancha": "cancha 2"`), sin grilla horaria ni forma de saber qué turnos existían. Este servicio se hace cargo de las canchas, sus turnos, los bloqueos de franjas y la disponibilidad. Tiene su propia base de datos y se entera de las reservas por eventos, sin leer la base del módulo de Reservas.

## Arquitectura

```
                         ┌──────────────────────────── servicio de Canchas ───────────────────────────┐
  Cliente / Reservas ──► │ canchas-api (FastAPI) ──► PostgreSQL (canchas-db)  ◄── canchas-consumidor  │ ◄── RabbitMQ: exchange "reservas"
       REST              │        │    ▲                    │ tabla outbox                             │       (ReservaCreada / ReservaCancelada)
                         │        ▼    │                    ▼                                          │
                         │      Redis (caché de            canchas-publicador ─────────────────────────┼──► RabbitMQ: exchange "canchas"
                         │      disponibilidad)                                                      │       (TurnoBloqueado / ReservaEnConflicto)
                         └────────────────────────────────────────────────────────────────────────────┘
```

| Contenedor | Qué hace |
|---|---|
| `canchas-api` | API REST (puerto **8002**). Canchas, bloqueos, disponibilidad, validación de turno y health check. |
| `canchas-consumidor` | Consume `ReservaCreada` y `ReservaCancelada` y actualiza la ocupación. Es idempotente y reintenta. |
| `canchas-publicador` | Lee la tabla `outbox` y publica los eventos del servicio con *publisher confirms*. |
| `canchas-db` | PostgreSQL 16, base propia del servicio (puerto 5433 en tu máquina). |
| `redis` | Caché de disponibilidad con TTL. |
| `rabbitmq` | Broker de mensajes. Panel web en http://localhost:15672 (guest / guest). |

La API, el consumidor y el publicador usan la misma imagen pero corren como procesos separados. Si el broker se cae, la API sigue atendiendo.

### Datos que administra el servicio

| Tabla | Contenido |
|---|---|
| `canchas` | Nombre, tipo (cristal/muro), techada, precio, horario de apertura y cierre, duración del turno, `activa` (baja lógica). |
| `bloqueos` | Franjas reservadas para uso interno (mantenimiento, torneos). |
| `ocupaciones` | Franjas ocupadas por reservas, **copia local** construida a partir de los eventos de Reservas. |
| `eventos_procesados` | `event_id` de cada evento ya aplicado (idempotencia del consumidor). |
| `outbox` | Eventos pendientes de publicar (patrón Transactional Outbox). |

El turno no es una tabla: se calcula en cada consulta a partir del horario y de la duración configurados en la cancha.

## Cómo ejecutarlo

Requisitos: Docker y Docker Compose. No hace falta tener Python instalado.

```bash
git clone https://github.com/Carlitoos22/sistema-reservas-padel.git
cd sistema-reservas-padel
git checkout ae2/juan-salazar
cd canchas

cp .env.example .env          # en Windows (PowerShell): copy .env.example .env
docker compose up -d --build
docker compose ps             # esperar a que todos figuren "running" / "healthy"
```

- Swagger (documentación interactiva): http://localhost:8002/docs
- Estado del servicio y sus dependencias: http://localhost:8002/health
- Panel de RabbitMQ: http://localhost:15672

Para apagar: `docker compose down`. Si además querés borrar los datos: `docker compose down -v`.

## Tests

```bash
# todos los tests, dentro del contenedor (incluye los de concurrencia contra PostgreSQL real)
docker compose exec canchas-api python -m pytest -v

# solo el caso de concurrencia
docker compose exec canchas-api python -m pytest tests/test_concurrencia_postgres.py -v
```

Los tests usan SQLite en memoria y un Redis falso (`fakeredis`), así que también corren sin Docker con `python -m pytest` desde `canchas/`. En ese caso se saltean los 3 de `test_concurrencia_postgres.py`, porque el *write skew* que prueban solo se puede reproducir con PostgreSQL.

| Archivo | Tests | Qué cubre |
|---|---|---|
| `test_canchas.py` | 10 | CRUD, validaciones de horario, nombre duplicado, baja lógica |
| `test_bloqueos.py` | 12 | Superposición, fecha pasada, fuera de horario, cancha inactiva |
| `test_disponibilidad.py` | 10 | Cálculo de la grilla y estados libre / bloqueado / ocupado |
| `test_validacion.py` | 8 | Cada motivo de rechazo del contrato con Reservas |
| `test_cache.py` | 9 | HIT/MISS, TTL, invalidación y funcionamiento con Redis caído |
| `test_ocupacion.py` | 12 | Consumidor: idempotencia, desorden, reintentos, cola de fallidos |
| `test_outbox.py` | 7 | Atomicidad del outbox, publisher confirms, broker caído |
| `test_conflicto.py` | 4 | `ReservaEnConflicto` y `reservas_afectadas` |
| `test_concurrencia_postgres.py` | 3 | Bloqueo y reserva simultáneos, con y sin lock |

## API

Contrato completo: [`docs/openapi.json`](../docs/openapi.json). Se regenera con `python -m scripts.exportar_openapi` desde `canchas/`, o se descarga de http://localhost:8002/openapi.json con el servicio levantado.

| Método | Ruta | Uso | Respuestas |
|---|---|---|---|
| GET | `/api/v1/canchas?incluir_inactivas=false` | Listar canchas | 200 |
| GET | `/api/v1/canchas/{id}` | Obtener una cancha | 200 · 404 |
| POST | `/api/v1/canchas` | Crear cancha | 201 · 409 nombre repetido · 422 |
| PUT | `/api/v1/canchas/{id}` | Modificar cancha | 200 · 404 · 409 · 422 |
| DELETE | `/api/v1/canchas/{id}` | Baja lógica | 204 · 404 |
| POST | `/api/v1/canchas/{id}/bloqueos` | Bloquear una franja | 201 · 404 · 409 superpuesto o inactiva · 422 |
| GET | `/api/v1/canchas/{id}/bloqueos?fecha=` | Listar bloqueos | 200 · 404 |
| DELETE | `/api/v1/bloqueos/{id}` | Quitar un bloqueo | 204 · 404 |
| GET | `/api/v1/canchas/{id}/disponibilidad?fecha=` | Turnos del día con su estado | 200 · 404 · 409 · 422 |
| GET | `/api/v1/canchas/{id}/turnos/validar?fecha=&hora_inicio=` | Validación para Reservas | 200 siempre que los parámetros sean válidos |
| GET | `/health` | Estado de DB, Redis y RabbitMQ | 200 ok · 503 degradado |

El endpoint de validación siempre responde 200 cuando los parámetros tienen formato válido, porque "el turno no se puede reservar" es una respuesta y no un error del servicio. Si el turno no es válido, `valido` viene en `false` y `motivo` es uno de `CANCHA_INEXISTENTE`, `CANCHA_INACTIVA`, `FECHA_PASADA`, `HORARIO_INVALIDO` o `TURNO_BLOQUEADO`.

## Redis

- **Patrón:** cache-aside. Se busca primero en Redis; si no está, se calcula desde PostgreSQL y se guarda.
- **Clave:** `canchas:disponibilidad:{cancha_id}:{fecha}`
- **TTL:** `CACHE_TTL_SEGUNDOS` (300 s por defecto, configurable en `.env`).
- **Invalidación:**
  - crear o quitar un bloqueo, o recibir un evento de reserva → se borra la clave de esa cancha y esa fecha;
  - modificar o dar de baja una cancha → se borran todas las fechas de esa cancha.
- **Degradación:** Redis no es la fuente de verdad. Si no responde, se calcula todo desde la base y se deja un aviso en el log.
- La respuesta de disponibilidad trae el header `X-Cache: HIT` o `X-Cache: MISS` para ver de dónde salió.

## RabbitMQ

El catálogo completo de eventos, con contratos JSON y garantías, está en [`docs/EVENTOS.md`](../docs/EVENTOS.md). En resumen:

| Evento | Productor → Consumidor | Exchange / routing key |
|---|---|---|
| `ReservaCreada` | Reservas → Canchas | `reservas` / `reserva.creada` |
| `ReservaCancelada` | Reservas → Canchas | `reservas` / `reserva.cancelada` |
| `TurnoBloqueado` | Canchas → Reservas | `canchas` / `turno.bloqueado` |
| `ReservaEnConflicto` | Canchas → Reservas | `canchas` / `turno.conflicto` |

Como la AE2 es individual, el módulo de Reservas se **simula** con dos scripts: `scripts/publicar_evento.py` (publica eventos de Reservas) y `scripts/escuchar_eventos.py` (muestra lo que publica Canchas).

## Demostración paso a paso

Con el servicio levantado. Los comandos `curl` son para bash; en Windows se pueden hacer los mismos pedidos desde Swagger (http://localhost:8002/docs). En los ejemplos se usa la fecha `2026-10-15`; si ya pasó, cambiala por una futura.

**1. Crear una cancha**

```bash
curl -X POST http://localhost:8002/api/v1/canchas -H "Content-Type: application/json" \
  -d '{"nombre":"Cancha 1","tipo":"cristal","techada":true,"precio_turno":15000,"hora_apertura":"08:00","hora_cierre":"23:00","duracion_turno_min":90}'
```

**2. Caché: consultar la disponibilidad dos veces**

```bash
curl -i "http://localhost:8002/api/v1/canchas/1/disponibilidad?fecha=2026-10-15"   # X-Cache: MISS
curl -i "http://localhost:8002/api/v1/canchas/1/disponibilidad?fecha=2026-10-15"   # X-Cache: HIT
docker compose exec redis redis-cli TTL canchas:disponibilidad:1:2026-10-15        # segundos que le quedan
```

**3. Evento de Reservas e idempotencia.** Se publica el mismo evento dos veces:

```bash
docker compose exec canchas-api python -m scripts.publicar_evento creada --reserva 10 --cancha 1 --fecha 2026-10-15 --hora 09:30 --repetir 2
docker compose logs canchas-consumidor --tail 20
```

El log muestra que el segundo evento se descarta por duplicado. En la disponibilidad, el turno de 09:30 aparece `ocupado` una sola vez y la respuesta vuelve a ser `MISS`, porque el evento invalidó la caché.

**4. Mensaje mal formado → cola de fallidos**

```bash
docker compose exec canchas-api python -m scripts.publicar_evento invalido
```

En el panel de RabbitMQ, la cola `canchas.reservas.fallidos` pasa a tener un mensaje.

**5. Bloqueo y publicación de `TurnoBloqueado`.** En una terminal aparte:

```bash
docker compose exec canchas-api python -m scripts.escuchar_eventos
```

En la terminal original:

```bash
curl -X POST http://localhost:8002/api/v1/canchas/1/bloqueos -H "Content-Type: application/json" \
  -d '{"fecha":"2026-10-15","hora_desde":"08:00","hora_hasta":"11:00","motivo":"Torneo"}'
```

El escuchador recibe `TurnoBloqueado` con la reserva 10 en `reservas_afectadas`.

**6. Broker caído y outbox**

```bash
docker compose stop rabbitmq
curl -X POST http://localhost:8002/api/v1/canchas/1/bloqueos -H "Content-Type: application/json" \
  -d '{"fecha":"2026-10-15","hora_desde":"20:00","hora_hasta":"23:00","motivo":"Mantenimiento"}'   # 201 igual
curl http://localhost:8002/health                                                                 # 503 degradado
docker compose start rabbitmq
docker compose logs canchas-publicador --tail 10                                                  # publica el pendiente
```

**7. Concurrencia**

```bash
docker compose exec canchas-api python -m pytest tests/test_concurrencia_postgres.py -v
```

La explicación del caso está en [`docs/CONCURRENCIA.md`](../docs/CONCURRENCIA.md).

## Trazabilidad

| Requerimiento | Issue | Endpoints / componente | Tests |
|---|---|---|---|
| Estructura, Docker y alcance | #1 | `docker-compose.yml`, `docs/ALCANCE_AE2_canchas.md` | — |
| RF-C1 Canchas | #2 | `/api/v1/canchas` | `test_canchas.py` |
| RF-C3 Bloqueos | #3 | `/canchas/{id}/bloqueos`, `/bloqueos/{id}` | `test_bloqueos.py` |
| RF-C2 Disponibilidad | #4 | `/canchas/{id}/disponibilidad` | `test_disponibilidad.py` |
| RF-C4 Validación de turno | #5 | `/canchas/{id}/turnos/validar` | `test_validacion.py` |
| Caché Redis | #6 | `app/cache.py` | `test_cache.py` |
| RF-C5 Ocupación por eventos | #7 | `canchas-consumidor` | `test_ocupacion.py` |
| Publicación de `TurnoBloqueado` | #8 | `canchas-publicador`, tabla `outbox` | `test_outbox.py` |
| Idempotencia y concurrencia | #9 | lock por cancha, `ReservaEnConflicto` | `test_conflicto.py`, `test_concurrencia_postgres.py` |
| Documentación | #10 | este README, `docs/` | — |

## Documentación

- [`docs/ALCANCE_AE2_canchas.md`](../docs/ALCANCE_AE2_canchas.md): alcance individual, estado heredado y qué queda fuera.
- [`docs/DECISIONES.md`](../docs/DECISIONES.md): decisiones de arquitectura y alternativas descartadas.
- [`docs/EVENTOS.md`](../docs/EVENTOS.md): catálogo de eventos.
- [`docs/CONCURRENCIA.md`](../docs/CONCURRENCIA.md): caso de concurrencia.
- [`docs/openapi.json`](../docs/openapi.json): contrato de la API.

## Fuera de esta entrega

Horarios distintos por día o por temporada, precios por franja horaria, autenticación y roles, frontend y QR/PDF. El QR y el PDF corresponden al comprobante de reserva, que es responsabilidad del módulo de Reservas. El detalle está en el documento de alcance.
