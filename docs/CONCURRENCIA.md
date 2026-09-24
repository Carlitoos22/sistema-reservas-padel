# Caso de concurrencia: bloqueo y reserva de la misma franja

## El escenario

El dueño del complejo bloquea una franja (por ejemplo, un torneo de 14:00 a 18:00) en el mismo momento en que un jugador reserva un turno dentro de esa franja. Las dos operaciones son legítimas y ninguna puede impedir a la otra: la reserva vive en el módulo de Reservas y el bloqueo en el de Canchas, y no hay una transacción que abarque a los dos servicios.

Lo que sí hay que garantizar es que **el choque siempre se detecte y se informe a Reservas**, para que avise o reprograme al jugador. El estado inválido a evitar es una reserva activa sobre una franja bloqueada que nadie informó: el jugador llega a una cancha cerrada.

## Dos caminos para informar el choque

| Orden en que Canchas se entera | Cómo se informa |
|---|---|
| Primero la reserva (`ReservaCreada`), después el bloqueo | `TurnoBloqueado` la incluye en `reservas_afectadas` |
| Primero el bloqueo, después la reserva | Al aplicar `ReservaCreada`, el consumidor encuentra el bloqueo y emite `ReservaEnConflicto` |

Los dos eventos salen por el outbox, en la misma transacción que el cambio que los origina.

## La carrera (write skew)

Con dos caminos no alcanza. Si las dos transacciones corren al mismo tiempo en PostgreSQL (aislamiento READ COMMITTED), puede pasar esto:

```
T1 (crear bloqueo)                      T2 (aplicar ReservaCreada)
lee ocupaciones de la franja: ninguna
                                        lee bloqueos de la franja: ninguno
guarda bloqueo + TurnoBloqueado
  con reservas_afectadas = []
COMMIT
                                        guarda ocupación, sin ReservaEnConflicto
                                        COMMIT
```

Cada transacción, por separado, tomó una decisión correcta con lo que veía. Juntas dejan un estado inválido: bloqueo y reserva sobre la misma franja, sin ningún aviso. No hay dos escrituras sobre la misma fila, así que ni una restricción `UNIQUE` ni un bloqueo de fila del dato escrito lo evitan.

## La solución

Las dos transacciones toman primero el **mismo lock**: la fila de la cancha, con `SELECT ... FOR UPDATE`. La creación de bloqueos ya lo tomaba (etapa 3, para evitar bloqueos superpuestos) y ahora también lo toma el consumidor.

Con eso se serializan: la segunda espera en el `FOR UPDATE` hasta que la primera confirma, y como en READ COMMITTED cada sentencia ve lo confirmado hasta ese momento, su lectura posterior ya encuentra lo que escribió la primera. El choque se informa por el camino que corresponda y exactamente una vez.

### Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Aislamiento SERIALIZABLE | Detecta el write skew, pero aborta una de las transacciones y obliga a reintentar; en el consumidor eso genera reintentos de mensajes y en la API errores 500 si no se reintenta. El lock explícito es más predecible y el caso está acotado a una cancha. |
| Lock en Redis | Agrega una dependencia más en el camino crítico y no es transaccional con PostgreSQL: el lock podría vencer antes del commit. |
| Rechazar la reserva desde Canchas | Canchas no es dueño de las reservas; la decisión de qué hacer con el jugador es de Reservas. Canchas informa, no modifica datos ajenos. |

### Costo

El lock serializa todas las operaciones de escritura sobre una misma cancha (bloqueos y eventos de reserva). En un complejo de pádel esas operaciones son pocas por minuto, así que la espera es despreciable. Operaciones sobre canchas distintas no se bloquean entre sí, y las consultas de disponibilidad no toman el lock.

## Cómo se demuestra

`tests/test_concurrencia_postgres.py` corre contra el PostgreSQL real del `docker compose`, en un esquema propio que se borra al final. Fuerza el intercalado de la tabla anterior: cada transacción, después de leer, espera a que la otra también haya leído.

- **Sin el lock** (se reemplaza el `FOR UPDATE` por una lectura común): el bloqueo y la reserva quedan guardados y el choque se informa **0 veces**. Es el problema.
- **Con el lock**, empezando primero el bloqueo o primero la reserva: el choque se informa **exactamente 1 vez**, por el camino que corresponde.

```
docker compose exec canchas-api python -m pytest tests/test_concurrencia_postgres.py -v
```
