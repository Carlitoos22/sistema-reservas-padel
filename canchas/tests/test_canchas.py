# Pruebas del CRUD de canchas (RF-C1)

CANCHA = {
    "nombre": "Cancha 1",
    "tipo": "cristal",
    "techada": True,
    "precio_turno": 15000,
    "hora_apertura": "08:00",
    "hora_cierre": "23:30",
    "duracion_turno_min": 90,
}


def crear(cliente, **cambios):
    return cliente.post("/api/v1/canchas", json={**CANCHA, **cambios})


def test_crear_cancha(cliente):
    r = crear(cliente)
    assert r.status_code == 201
    assert r.json()["id"] == 1
    assert r.json()["activa"] is True


def test_obtener_cancha_inexistente_da_404(cliente):
    assert cliente.get("/api/v1/canchas/99").status_code == 404


def test_nombre_duplicado_da_409(cliente):
    crear(cliente)
    assert crear(cliente).status_code == 409


def test_tipo_invalido_da_422(cliente):
    assert crear(cliente, tipo="cemento").status_code == 422


def test_precio_negativo_da_422(cliente):
    assert crear(cliente, precio_turno=-100).status_code == 422


def test_cierre_antes_de_apertura_da_422(cliente):
    assert crear(cliente, hora_apertura="22:00", hora_cierre="08:00").status_code == 422


def test_horario_menor_a_un_turno_da_422(cliente):
    assert crear(cliente, hora_apertura="22:00", hora_cierre="23:00").status_code == 422


def test_actualizar_cancha(cliente):
    crear(cliente)
    r = cliente.put("/api/v1/canchas/1", json={**CANCHA, "precio_turno": 18000})
    assert r.status_code == 200
    assert float(r.json()["precio_turno"]) == 18000


def test_actualizar_con_nombre_de_otra_da_409(cliente):
    crear(cliente)
    crear(cliente, nombre="Cancha 2")
    r = cliente.put("/api/v1/canchas/2", json=CANCHA)
    assert r.status_code == 409


def test_baja_logica(cliente):
    crear(cliente)
    assert cliente.delete("/api/v1/canchas/1").status_code == 204
    # ya no aparece en el listado normal...
    assert cliente.get("/api/v1/canchas").json() == []
    # ...pero sigue guardada en la base, inactiva
    todas = cliente.get("/api/v1/canchas?incluir_inactivas=true").json()
    assert len(todas) == 1 and todas[0]["activa"] is False
