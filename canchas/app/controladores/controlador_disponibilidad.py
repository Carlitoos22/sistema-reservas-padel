from datetime import date, datetime, time, timedelta
from sqlalchemy.orm import Session
from app.datos import repositorio_canchas, repositorio_bloqueos, repositorio_ocupaciones
from app import cache
from app.modelos.disponibilidad import Disponibilidad, Turno, EstadoTurno
from app.controladores.controlador_canchas import CanchaNoEncontrada
from app.controladores.controlador_bloqueos import CanchaInactiva, FechaPasada

# ===== CAPA DE CONTROLADORES: Disponibilidad =====


def generar_turnos(apertura: time, cierre: time, duracion_min: int):
    """Divide el horario de la cancha en turnos consecutivos de igual duración.
    Si el último no entra completo antes del cierre, no se ofrece.

    Ejemplo: 08:00 a 23:30 con turnos de 90 min
    -> 08:00-09:30, 09:30-11:00, ..., 21:30-23:00  (10 turnos; 23:00-00:30 no entra)
    """
    hoy = date.today()
    inicio = datetime.combine(hoy, apertura)
    fin_del_dia = datetime.combine(hoy, cierre)
    paso = timedelta(minutes=duracion_min)

    turnos = []
    while inicio + paso <= fin_del_dia:
        turnos.append((inicio.time(), (inicio + paso).time()))
        inicio += paso
    return turnos


def se_superponen(desde_a: time, hasta_a: time, desde_b: time, hasta_b: time):
    return desde_a < hasta_b and desde_b < hasta_a


def consultar_disponibilidad(sesion: Session, id_cancha: int, fecha: date):
    """Devuelve (disponibilidad, origen), donde origen es "HIT" si vino de Redis
    o "MISS" si se calculó desde la base."""
    cancha = repositorio_canchas.buscar_por_id(sesion, id_cancha)
    if cancha is None:
        raise CanchaNoEncontrada()
    if not cancha.activa:
        raise CanchaInactiva()
    if fecha < date.today():
        raise FechaPasada()

    # Las validaciones de arriba se hacen siempre contra la base (son baratas y
    # garantizan que nunca se sirva caché de una cancha dada de baja).
    clave = cache.clave_disponibilidad(id_cancha, fecha)
    guardado = cache.leer(clave)
    if guardado is not None:
        return Disponibilidad.model_validate_json(guardado), "HIT"

    bloqueos = repositorio_bloqueos.listar_por_cancha(sesion, id_cancha, fecha)
    ocupaciones = repositorio_ocupaciones.listar_activas(sesion, id_cancha, fecha)

    turnos = []
    for inicio, fin in generar_turnos(cancha.hora_apertura, cancha.hora_cierre, cancha.duracion_turno_min):
        # Bloqueado tiene prioridad: es una decisión del dueño del complejo.
        # (No deberían coincidir, porque la validación rechaza turnos bloqueados.)
        if any(se_superponen(inicio, fin, b.hora_desde, b.hora_hasta) for b in bloqueos):
            estado = EstadoTurno.bloqueado
        elif any(se_superponen(inicio, fin, o.hora_inicio, o.hora_fin) for o in ocupaciones):
            estado = EstadoTurno.ocupado
        else:
            estado = EstadoTurno.libre
        turnos.append(Turno(hora_inicio=inicio, hora_fin=fin, estado=estado))

    resultado = Disponibilidad(cancha_id=id_cancha, fecha=fecha, turnos=turnos)
    cache.guardar(clave, resultado.model_dump_json())
    return resultado, "MISS"
