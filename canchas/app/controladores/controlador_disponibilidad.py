from datetime import date, datetime, time, timedelta
from sqlalchemy.orm import Session
from app.datos import repositorio_canchas, repositorio_bloqueos
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


def consultar_disponibilidad(sesion: Session, id_cancha: int, fecha: date) -> Disponibilidad:
    cancha = repositorio_canchas.buscar_por_id(sesion, id_cancha)
    if cancha is None:
        raise CanchaNoEncontrada()
    if not cancha.activa:
        raise CanchaInactiva()
    if fecha < date.today():
        raise FechaPasada()

    bloqueos = repositorio_bloqueos.listar_por_cancha(sesion, id_cancha, fecha)

    turnos = []
    for inicio, fin in generar_turnos(cancha.hora_apertura, cancha.hora_cierre, cancha.duracion_turno_min):
        bloqueado = any(se_superponen(inicio, fin, b.hora_desde, b.hora_hasta) for b in bloqueos)
        estado = EstadoTurno.bloqueado if bloqueado else EstadoTurno.libre
        turnos.append(Turno(hora_inicio=inicio, hora_fin=fin, estado=estado))

    return Disponibilidad(cancha_id=id_cancha, fecha=fecha, turnos=turnos)
