"""Pruebas del rol de administrador: control de acceso, alta segura del dueño,
resumen, gestión de reservas y de usuarios.
    python -m pytest pruebas/ -k admin -v
"""
import os

import pytest
from fastapi.testclient import TestClient

from pruebas.test_admin_canchas import entrar, crear_reserva_directa, base_limpia  # noqa: F401
from app.main import app
from app.database import SessionLocal
from app.controladores import controlador_admin
from app.datos import repositorio_reservas, repositorio_usuarios

# Todas las acciones de administración: (método, ruta, datos)
ACCIONES_ADMIN = [
    ("get", "/admin", None),
    ("get", "/admin/canchas", None),
    ("get", "/admin/reservas", None),
    ("get", "/admin/usuarios", None),
    ("post", "/admin/canchas/crear", {"nombre": "Pirata", "tipo": "Muro"}),
    ("post", "/admin/canchas/1/editar", {"nombre": "Pirata", "tipo": "Muro"}),
    ("post", "/admin/canchas/1/estado", None),
    ("post", "/admin/canchas/1/eliminar", None),
    ("post", "/admin/reservas/1/cancelar", None),
    ("post", "/admin/usuarios/1/rol", {"rol": "dueño"}),
]


def _pedir(cliente, metodo, ruta, datos, **kw):
    return getattr(cliente, metodo)(ruta, data=datos, **kw) if datos else getattr(cliente, metodo)(ruta, **kw)


# ---------- El jugador no puede hacer NADA de administración ----------

@pytest.mark.parametrize("metodo, ruta, datos", ACCIONES_ADMIN, ids=[f"{m} {r}" for m, r, _ in ACCIONES_ADMIN])
def test_jugador_recibe_403_en_todas_las_acciones(metodo, ruta, datos):
    crear_reserva_directa("Cancha 1")
    jugador = entrar("jugador")
    assert _pedir(jugador, metodo, ruta, datos).status_code == 403
    # Nada cambió: la reserva sigue, la cancha sigue y el jugador sigue siendo jugador
    with SessionLocal() as db:
        assert len(repositorio_reservas.listar(db)) == 1
        assert repositorio_usuarios.buscar_por_email(db, "jugador@padel.com").rol == "jugador"


@pytest.mark.parametrize("metodo, ruta, datos", ACCIONES_ADMIN, ids=[f"{m} {r}" for m, r, _ in ACCIONES_ADMIN])
def test_sin_sesion_todas_las_acciones_mandan_al_login(metodo, ruta, datos):
    r = _pedir(TestClient(app), metodo, ruta, datos, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


# ---------- Alta segura del dueño ----------

def test_el_registro_publico_ignora_el_rol_dueno():
    # Aunque se arme el formulario a mano con rol=dueño, queda como jugador
    cliente = TestClient(app)
    cliente.post("/registro", data={"nombre": "Vivo", "email": "vivo@padel.com",
                                    "password": "x", "rol": "dueño"})
    with SessionLocal() as db:
        assert repositorio_usuarios.buscar_por_email(db, "vivo@padel.com").rol == "jugador"


def test_el_formulario_de_registro_ya_no_ofrece_el_rol():
    assert "Dueño" not in TestClient(app).get("/registro").text


def test_dueno_inicial_por_variables_de_entorno(monkeypatch):
    monkeypatch.setenv("DUENO_EMAIL", "admin@padel.com")
    monkeypatch.setenv("DUENO_PASSWORD", "secreta")
    with SessionLocal() as db:
        controlador_admin.crear_dueno_inicial(db)
        controlador_admin.crear_dueno_inicial(db)   # dos veces: no duplica
        assert repositorio_usuarios.buscar_por_email(db, "admin@padel.com").rol == "dueño"
        assert repositorio_usuarios.contar_por_rol(db, "dueño") == 1
    cliente = TestClient(app)
    cliente.post("/login", data={"email": "admin@padel.com", "password": "secreta"})
    assert cliente.get("/admin").status_code == 200


def test_sin_variables_de_entorno_no_se_crea_ningun_dueno(monkeypatch):
    monkeypatch.delenv("DUENO_EMAIL", raising=False)
    with SessionLocal() as db:
        assert controlador_admin.crear_dueno_inicial(db) is None
        assert repositorio_usuarios.contar_por_rol(db, "dueño") == 0


# ---------- Resumen ----------

def test_resumen_calcula_la_ocupacion_del_dia():
    crear_reserva_directa("Cancha 1")          # 2026-12-01 18:00
    r = entrar().get("/admin?fecha=2026-12-01")
    assert r.status_code == 200
    with SessionLocal() as db:
        datos = controlador_admin.resumen(db, "2026-12-01")
    # 3 canchas activas x 5 horarios = 15 turnos; 1 ocupado = 7 %
    assert (datos["turnos_totales"], datos["turnos_ocupados"], datos["ocupacion"]) == (15, 1, 7)
    assert "7%" in r.text


def test_resumen_con_fecha_invalida_no_rompe():
    assert entrar().get("/admin?fecha=no-es-fecha").status_code == 200


# ---------- Reservas ----------

def test_el_dueno_ve_las_reservas_de_todos_y_filtra():
    crear_reserva_directa("Cancha 1")
    crear_reserva_directa("Cancha 2")
    dueno = entrar()
    todas = dueno.get("/admin/reservas").text
    assert "2 reservas" in todas
    filtrada = dueno.get("/admin/reservas?cancha=Cancha 2").text
    assert "1 reserva" in filtrada and "<strong>Cancha 1</strong>" not in filtrada


def test_el_dueno_cancela_cualquier_reserva_y_el_turno_queda_libre():
    crear_reserva_directa("Cancha 1")
    dueno = entrar()
    r = dueno.post("/admin/reservas/1/cancelar")
    assert "Reserva cancelada" in r.text
    with SessionLocal() as db:
        assert repositorio_reservas.listar(db) == []
    assert "Esa reserva ya no existe" in dueno.post("/admin/reservas/1/cancelar").text


# ---------- Usuarios y roles ----------

def test_el_dueno_promueve_a_un_jugador_y_este_entra_al_panel():
    jugador = entrar("jugador")
    dueno = entrar()
    with SessionLocal() as db:
        id_jugador = repositorio_usuarios.buscar_por_email(db, "jugador@padel.com").id
    r = dueno.post(f"/admin/usuarios/{id_jugador}/rol", data={"rol": "dueño"})
    assert "Rol actualizado" in r.text
    # La autorización se lee de la base en cada pedido: no hace falta volver a entrar
    assert jugador.get("/admin").status_code == 200


def test_el_dueno_no_puede_quitarse_su_propio_rol():
    dueno = entrar()
    with SessionLocal() as db:
        mi_id = repositorio_usuarios.buscar_por_email(db, "dueño@padel.com").id
    r = dueno.post(f"/admin/usuarios/{mi_id}/rol", data={"rol": "jugador"})
    assert "No podés cambiar tu propio rol" in r.text
    assert dueno.get("/admin").status_code == 200


def test_rol_inventado_se_rechaza():
    entrar("jugador")
    dueno = entrar()
    r = dueno.post("/admin/usuarios/1/rol", data={"rol": "superadmin"})
    assert "Rol inválido" in r.text


# ---------- API REST ----------

def test_la_api_no_deja_borrar_ni_modificar_reservas_sin_ser_dueno():
    crear_reserva_directa("Cancha 1")
    jugador = entrar("jugador")
    assert TestClient(app).delete("/api/v1/reservas/1").status_code == 401
    assert jugador.delete("/api/v1/reservas/1").status_code == 403
    cambio = {"nombre_jugador": "X", "cancha": "Cancha 1", "fecha": "2026-12-01", "hora": "19:30"}
    assert jugador.put("/api/v1/reservas/1", json=cambio).status_code == 403
    assert entrar().delete("/api/v1/reservas/1").status_code == 204
