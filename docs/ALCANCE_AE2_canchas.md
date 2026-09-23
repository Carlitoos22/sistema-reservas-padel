# AE2 – Alcance individual: Módulo de Canchas y Disponibilidad

**Estudiante:** Salazar, Juan Martín
**Branch:** `ae2/juan-salazar`
**Materia:** Paradigmas y Lenguajes de Programación III – UCP – 2026

## 1. Escenario

Sistema de reservas de turnos para canchas de pádel (mismo escenario del AE1, desarrollado con Alfaro, Carlos Tomás).

## 2. Versión base del AE1

Repositorio: https://github.com/Carlitoos22/sistema-reservas-padel
Versión de partida: `<completar con el tag/commit indicado por la cátedra>` (último commit de la entrega AE1: `b8204f0`).

## 3. Módulo seleccionado

**Canchas y Disponibilidad.** En el AE1 este módulo quedó definido en el modelo de dominio (entidades Cancha y Turno, sección 2 del informe), pero sin implementación: la cancha existe solamente como un texto libre dentro de la entidad Reserva (`"cancha": "cancha 2"`). En la AE2 se extrae a un servicio propio, con sus datos y su API.

La división con mi compañero es la siguiente: él evoluciona el módulo de Reservas (incluida la prevención de doble reserva) y yo el de Canchas y Disponibilidad.

## 4. Estado inicial heredado del AE1

- API FastAPI con arquitectura en capas (rutas, controladores, datos, modelos), un solo recurso: Reserva.
- Persistencia en archivo JSON, sin tipos: fecha, hora, cancha y estado son strings sin validar.
- No hay entidad Cancha ni concepto de grilla horaria, por lo que el sistema no puede saber qué turnos existen ni cuáles están libres.
- Los endpoints son síncronos (`def`) y FastAPI los ejecuta en un pool de hilos; con 30 pedidos simultáneos se comprobaron IDs duplicados, reservas perdidas y errores 500.
- Sin Docker, sin tests, sin Redis ni RabbitMQ.

## 5. Requerimientos funcionales comprometidos

| ID | Requerimiento |
|----|---------------|
| RF-C1 | Alta, consulta, modificación y baja lógica de canchas (nombre, tipo, techada, precio, horario de apertura/cierre y duración del turno). |
| RF-C2 | Consulta de disponibilidad de una cancha para una fecha: lista de turnos con estado libre, ocupado o bloqueado. |
| RF-C3 | Registro de bloqueos de franjas horarias (mantenimiento, torneos). Una franja bloqueada no se ofrece como disponible. |
| RF-C4 | Validación de turno: endpoint que el módulo de Reservas consulta para verificar que la cancha existe, está activa y que el horario corresponde a un turno válido de su grilla. |
| RF-C5 | Actualización de la ocupación a partir de los eventos `ReservaCreada` y `ReservaCancelada` publicados por el módulo de Reservas. |

## 6. Requerimientos no funcionales relacionados

- **Propiedad de datos:** el módulo tiene su propia base PostgreSQL. No lee la base de Reservas; conoce la ocupación únicamente por eventos.
- **Caché con Redis:** la disponibilidad por cancha y fecha se guarda en caché con TTL y se invalida ante eventos de reserva o al crear un bloqueo.
- **Mensajería con RabbitMQ:** consumo de `ReservaCreada` / `ReservaCancelada` y publicación de `TurnoBloqueado`.
- **Idempotencia:** un evento repetido o recibido fuera de orden no debe dejar la ocupación en un estado inconsistente.
- **Contratos:** API documentada con OpenAPI; catálogo de eventos documentado.
- **Reproducibilidad:** ejecución con Docker Compose y tests automatizados.
- **Health check:** endpoint que informa el estado de la base, Redis y RabbitMQ.

## 7. Dependencias con otros componentes

- **Módulo de Reservas (compañero):** publica los eventos que consume este módulo y consulta RF-C4 de forma síncrona. En este branch sus eventos se simulan con un script publicador, ya que el desarrollo es individual.
- **Redis y RabbitMQ:** infraestructura compartida en la integración de AE4.

## 8. Alcance comprometido en AE2

RF-C1 a RF-C5, con caché, mensajería, idempotencia del consumidor, un caso de concurrencia demostrado (bloqueo de una franja en simultáneo con una reserva de esa franja), tests y documentación.

## 9. Fuera de esta entrega

- Horarios distintos por día de la semana o por temporada (la grilla es única por cancha).
- Precios diferenciales por horario.
- Generación de QR y PDF: corresponden al comprobante de reserva, que es responsabilidad del módulo de Reservas.
- Autenticación y roles: se asume que las operaciones de administración las realiza el dueño del complejo.
- Frontend.
