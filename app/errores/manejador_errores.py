from fastapi import Request
from fastapi.responses import JSONResponse

# ===== MIDDLEWARE / MANEJADOR CENTRALIZADO DE ERRORES =====
# Captura cualquier error no controlado y devuelve un JSON
# estructurado con código 500, en vez de que el servidor se rompa.

async def manejador_errores_general(request: Request, exc: Exception):
    """Captura cualquier excepción no controlada y responde un 500 en JSON."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "detalle": str(exc)
        }
    )