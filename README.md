# API de Reservas de Pádel — Módulo de Reservas

API RESTful para la gestión de reservas de turnos en canchas de pádel.
Este repositorio corresponde a la asignatura **Paradigmas y Lenguajes de
Programación III (UCP)**. La versión actual es la **evolución individual
del AE2 (v2.0)** del **módulo de Reservas**, desarrollada sobre la base
grupal del AE1 (tag `v1.0-ae1`).

## Integrantes y módulos

- **Alfaro, Carlos Tomás** — Módulo de Reservas · branch `ae2/alfaro`
- **Salazar, Juan Martín** — Módulo de Canchas y Disponibilidad · branch `ae2/juan-salazar`

## Tecnologías

- **Python + FastAPI** — API REST (comunicación síncrona)
- **PostgreSQL** — persistencia relacional
- **SQLAlchemy** — ORM (acceso a datos)
- **Redis** — candado de concurrencia e idempotencia
- **RabbitMQ** — mensajería asíncrona (eventos)
- **Docker / Docker Compose** — ejecución contenerizada de la infraestructura

## Arquitectura

El proyecto mantiene la arquitectura en capas del AE1:

- `app/rutas/` — definición de los endpoints
- `app/controladores/` — coordinación y lógica de negocio
- `app/datos/` — acceso a datos (repositorio con el ORM)
- `app/modelos/` — entidades y modelo de tabla
- `app/errores/` — manejo centralizado de errores

Piezas incorporadas en el AE2:

- `app/database.py` — conexión a PostgreSQL
- `app/redis_client.py` — conexión a Redis
- `app/rabbitmq_client.py` — productor de eventos (RabbitMQ)
- `consumidor.py` — consumidor de eventos (proceso independiente)
- `docker-compose.yml` — servicios de PostgreSQL, Redis y RabbitMQ

## Requisitos previos

- Docker Desktop (con WSL2 en Windows)
- Python 3.x

## Cómo ejecutar

**1. Levantar la infraestructura (PostgreSQL, Redis y RabbitMQ):**

```
docker compose up -d
```

**2. Instalar las dependencias:**

```
pip install -r requirements.txt
```

**3. Levantar la API (en una terminal):**

```
python -m uvicorn app.main:app --reload
```

**4. Levantar el consumidor de eventos (en otra terminal):**

```
python consumidor.py
```

**5. Abrir la documentación interactiva:**

```
http://127.0.0.1:8000/docs
```

## Endpoints principales (entidad Reserva)

| Método | Endpoint | Acción | Código |
|--------|----------|--------|--------|
| GET | /api/v1/reservas | Listar reservas | 200 |
| GET | /api/v1/reservas/{id} | Obtener una reserva | 200 / 404 |
| POST | /api/v1/reservas | Crear una reserva | 201 / 400 / 409 |
| PUT | /api/v1/reservas/{id} | Actualizar una reserva | 200 / 404 |
| DELETE | /api/v1/reservas/{id} | Eliminar una reserva | 204 / 404 |

## Funcionalidades incorporadas en el AE2

- **RF-A — Concurrencia:** candado atómico en Redis (`SET NX` con TTL)
  sobre el turno. Evita la doble reserva; el segundo intento recibe **409**.
- **RF-B — Idempotencia:** cabecera `Idempotency-Key`. Un pedido repetido
  devuelve la reserva original, sin crear duplicados.
- **RF-C — Comunicación asíncrona:** al confirmar una reserva se publica el
  evento `reserva_confirmada` en RabbitMQ; un consumidor independiente lo
  procesa sin bloquear el flujo principal.
- **Migración de persistencia:** de archivo JSON a PostgreSQL con SQLAlchemy.

## Cómo verificar (pruebas)

- **Crear:** POST de un turno nuevo → `201 Created`.
- **Concurrencia (RF-A):** POST del mismo turno → `409 Conflict`.
- **Idempotencia (RF-B):** dos POST con la misma `Idempotency-Key` → mismo `id`.
- **Mensajería (RF-C):** el consumidor muestra el evento recibido en su terminal.
- **Persistencia:** `docker exec -it padel_postgres psql -U padel_user -d padel_db`
  y luego `SELECT * FROM reservas;`

## Trazabilidad

- Versión base AE1: tag `v1.0-ae1` (commit `b8204f0`)
- Branch individual: `ae2/alfaro`
- La evolución se registra en el historial de commits del branch.
