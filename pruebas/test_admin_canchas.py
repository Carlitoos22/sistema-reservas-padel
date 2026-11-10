"""Pruebas del módulo de administración de canchas (rol dueño).

Corren con una base SQLite temporal, sin PostgreSQL, Redis ni RabbitMQ:
    pip install -r requirements-dev.txt
    python -m pytest pruebas/test_admin_canchas.py -v
"""
import os
import tempfile

# La base de prueba se configura ANTES de importar la app
_archivo_db = os.path.join(tempfile.mkdtemp(), "pruebas.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_archivo_db}"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.controladores import controlador_canchas
from app.datos import repositorio_reservas, repositorio_usuarios
from app.modelos.cancha import CanchaDB


@pytest.fixture(autouse=True)
def base_limpia():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        controlador_canchas.cargar_canchas_iniciales(db)
    yield


def entrar(rol="dueño", email=None):
    """Registra un usuario por el formulario público (siempre queda como jugador)
    y, si se pide dueño, lo promueve directo en la base. Después inicia sesión."""
    cliente = TestClient(app)
    email = email or f"{rol}@padel.com"
    cliente.post("/registro", data={"nombre": rol.capitalize(), "email": email, "password": "clave123"})
    if rol == "dueño":
        with SessionLocal() as db:
            u = repositorio_usuarios.buscar_por_email(db, email)
            repositorio_usuarios.cambiar_rol(db, u.id, "dueño")
    cliente.post("/login", data={"email": email, "password": "clave123"})
    return cliente


def canchas_en_base():
    with SessionLocal() as db:
        return [(c.nombre, c.tipo, c.activa) for c in db.query(CanchaDB).order_by(CanchaDB.id)]


def crear_reserva_directa(cancha):
    # Directo al repositorio para no depender de Redis ni RabbitMQ
    with SessionLocal() as db:
        repositorio_reservas.crear(db, {"nombre_jugador": "Jugador", "cancha": cancha,
                                        "fecha": "2026-12-01", "hora": "18:00"})


# ---------- Carga inicial (reemplazo de canchas_demo.py) ----------

def test_base_vacia_arranca_con_las_tres_canchas_iniciales():
    assert [n for n, _, _ in canchas_en_base()] == ["Cancha 1", "Cancha 2", "Cancha 3"]


def test_la_carga_inicial_no_duplica_si_ya_hay_canchas():
    with SessionLocal() as db:
        controlador_canchas.cargar_canchas_iniciales(db)
    assert len(canchas_en_base()) == 3


# ---------- Control de acceso ----------

def test_sin_sesion_el_panel_manda_al_login():
    r = TestClient(app).get("/admin/canchas", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_un_jugador_no_puede_entrar_al_panel_403():
    jugador = entrar("jugador")
    r = jugador.get("/admin/canchas")
    assert r.status_code == 403 and "Acceso denegado" in r.text
    assert jugador.post("/admin/canchas/crear", data={"nombre": "Pirata", "tipo": "Muro"}).status_code == 403
    assert "Pirata" not in [n for n, _, _ in canchas_en_base()]


def test_el_dueno_ve_el_panel_y_el_link_de_administracion():
    dueno = entrar()
    r = dueno.get("/admin/canchas")
    assert r.status_code == 200
    assert "Administrar canchas" in r.text and "Cancha 1" in r.text
    assert 'href="/admin"' in dueno.get("/canchas").text


def test_el_jugador_no_ve_el_link_de_administracion():
    assert 'href="/admin"' not in entrar("jugador").get("/canchas").text


# ---------- Crear ----------

def test_crear_cancha_aparece_en_la_vista_de_reservas():
    dueno = entrar()
    r = dueno.post("/admin/canchas/crear", data={"nombre": "Cancha 4", "tipo": "Muro - techada"})
    assert "Cancha creada" in r.text
    vista = entrar("jugador").get("/canchas").text
    assert "Cancha 4" in vista and "Muro - techada" in vista


def test_crear_con_nombre_repetido_no_duplica():
    dueno = entrar()
    r = dueno.post("/admin/canchas/crear", data={"nombre": "cancha 1", "tipo": "Muro"})
    assert "Ya existe una cancha con ese nombre" in r.text
    assert len(canchas_en_base()) == 3


@pytest.mark.parametrize("nombre", ["<script>alert(1)</script>", "Cancha'; DROP TABLE canchas;--", "   "])
def test_crear_con_texto_malicioso_o_vacio_se_rechaza(nombre):
    dueno = entrar()
    r = dueno.post("/admin/canchas/crear", data={"nombre": nombre, "tipo": "Cristal"})
    assert r.status_code == 200 and "Datos inválidos" in r.text
    assert len(canchas_en_base()) == 3


# ---------- Editar ----------

def test_editar_nombre_y_tipo_sin_reservas():
    dueno = entrar()
    r = dueno.post("/admin/canchas/1/editar", data={"nombre": "Cancha Central", "tipo": "Cristal - exterior"})
    assert "Cambios guardados" in r.text
    assert canchas_en_base()[0] == ("Cancha Central", "Cristal - exterior", True)


def test_no_se_renombra_una_cancha_con_reservas_pero_si_cambia_el_tipo():
    crear_reserva_directa("Cancha 1")
    dueno = entrar()
    r = dueno.post("/admin/canchas/1/editar", data={"nombre": "Otra", "tipo": "Cristal - techada"})
    assert "No se puede cambiar el nombre" in r.text
    r = dueno.post("/admin/canchas/1/editar", data={"nombre": "Cancha 1", "tipo": "Muro - techada"})
    assert "Cambios guardados" in r.text
    assert canchas_en_base()[0] == ("Cancha 1", "Muro - techada", True)


def test_editar_con_el_nombre_de_otra_cancha_se_rechaza():
    r = entrar().post("/admin/canchas/1/editar", data={"nombre": "Cancha 2", "tipo": "Muro"})
    assert "Ya existe una cancha con ese nombre" in r.text


# ---------- Activar / desactivar ----------

def test_cancha_desactivada_no_se_ofrece_ni_se_puede_reservar():
    dueno = entrar()
    r = dueno.post("/admin/canchas/2/estado")
    assert "quedó desactivada" in r.text

    jugador = entrar("jugador")
    assert "Cancha 2" not in jugador.get("/canchas").text
    r = jugador.post("/reservar", data={"cancha": "Cancha 2", "fecha": "2026-12-01", "hora": "14:00 - 16:00"})
    assert "no está disponible" in r.text

    dueno.post("/admin/canchas/2/estado")
    assert "Cancha 2" in jugador.get("/canchas").text


def test_no_se_puede_reservar_un_horario_inventado():
    r = entrar("jugador").post("/reservar", data={"cancha": "Cancha 1", "fecha": "2026-12-01", "hora": "03:00"})
    assert "no está disponible" in r.text


# ---------- Eliminar ----------

def test_eliminar_cancha_sin_reservas():
    r = entrar().post("/admin/canchas/3/eliminar")
    assert "Cancha eliminada" in r.text
    assert "Cancha 3" not in [n for n, _, _ in canchas_en_base()]


def test_no_se_elimina_una_cancha_con_reservas():
    crear_reserva_directa("Cancha 3")
    r = entrar().post("/admin/canchas/3/eliminar")
    assert "No se puede eliminar" in r.text
    assert "Cancha 3" in [n for n, _, _ in canchas_en_base()]


def test_operar_sobre_una_cancha_inexistente():
    dueno = entrar()
    assert "Esa cancha no existe" in dueno.post("/admin/canchas/99/eliminar").text
    assert "Esa cancha no existe" in dueno.post("/admin/canchas/99/estado").text


# ---------- Seguridad HTTP ----------

def test_el_panel_lleva_los_headers_de_seguridad():
    r = entrar().get("/admin/canchas")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
