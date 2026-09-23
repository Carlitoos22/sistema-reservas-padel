from datetime import date, time
from sqlalchemy.orm import Session
from app.datos import repositorio_canchas, repositorio_bloqueos
from app.modelos.validacion import ResultadoValidacion, MotivoRechazo
from app.controladores.controlador_disponibilidad import generar_turnos, se_superponen

# ===== CAPA DE CONTROLADORES: Validación de turno (RF-C4) =====
# Responde si un turno existe en la grilla de la cancha y no está bloqueado.
# No verifica si ya está reservado: eso lo decide el módulo de Reservas,
# que es el dueño de las reservas y la autoridad final sobre la ocupación.


def validar_turno(sesion: Session, id_cancha: int, fecha: date, hora_inicio: time) -> ResultadoValidacion:
    def rechazo(motivo: MotivoRechazo):
        return ResultadoValidacion(
            valido=False, motivo=motivo, cancha_id=id_cancha, fecha=fecha, hora_inicio=hora_inicio
        )

    cancha = repositorio_canchas.buscar_por_id(sesion, id_cancha)
    if cancha is None:
        return rechazo(MotivoRechazo.cancha_inexistente)
    if not cancha.activa:
        return rechazo(MotivoRechazo.cancha_inactiva)
    if fecha < date.today():
        return rechazo(MotivoRechazo.fecha_pasada)

    turnos = generar_turnos(cancha.hora_apertura, cancha.hora_cierre, cancha.duracion_turno_min)
    turno = next(((ini, fin) for ini, fin in turnos if ini == hora_inicio), None)
    if turno is None:
        return rechazo(MotivoRechazo.horario_invalido)

    inicio, fin = turno
    bloqueos = repositorio_bloqueos.listar_por_cancha(sesion, id_cancha, fecha)
    if any(se_superponen(inicio, fin, b.hora_desde, b.hora_hasta) for b in bloqueos):
        return rechazo(MotivoRechazo.turno_bloqueado)

    return ResultadoValidacion(
        valido=True,
        cancha_id=id_cancha,
        fecha=fecha,
        hora_inicio=inicio,
        hora_fin=fin,
        precio_turno=cancha.precio_turno,
    )
