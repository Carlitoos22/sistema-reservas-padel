# API de Reservas de Pádel

API RESTful para la gestión de reservas de turnos en canchas de pádel. Proyecto desarrollado para la Actividad de Evaluación N°1 (AE1) de la asignatura Paradigmas y Lenguajes de Programación III - UCP.

## Integrantes
- Salazar, Juan Martín
- Alfaro, Carlos Tomás

## Tecnologías
- Python
- FastAPI
- Persistencia en archivo JSON

## Ejecución
Instalar dependencias: pip install -r requirements.txt

Ejecutar el servidor: python -m uvicorn app.main:app --reload

Luego abrir en el navegador: http://127.0.0.1:8000/docs

## Endpoints principales (entidad Reserva)
- GET /api/v1/reservas - Listar todas las reservas
- GET /api/v1/reservas/{id} - Obtener una reserva
- POST /api/v1/reservas - Crear una reserva
- PUT /api/v1/reservas/{id} - Actualizar una reserva
- DELETE /api/v1/reservas/{id} - Eliminar una reserva