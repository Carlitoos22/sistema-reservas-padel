"""
Consigna 3 (Headers de seguridad) + Consigna 2 (Error 400 limpio).
Se enchufa desde main.py con: aplicar_seguridad_http(app)
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


def aplicar_seguridad_http(app):

    # --- Consigna 3: cabeceras de seguridad en cada respuesta ---
    @app.middleware("http")
    async def _cabeceras_seguridad(request: Request, call_next):
        respuesta = await call_next(request)
        respuesta.headers["X-Content-Type-Options"] = "nosniff"       # anti-sniffing
        respuesta.headers["X-Frame-Options"] = "DENY"                 # anti-clickjacking
        respuesta.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        respuesta.headers["Referrer-Policy"] = "no-referrer"
        return respuesta

    # --- Consigna 2: toda entrada inválida -> 400 Bad Request (nunca 500) ---
    @app.exception_handler(RequestValidationError)
    async def _validacion_a_400(request: Request, exc: RequestValidationError):
        errores = [
            {
                "campo": ".".join(str(parte) for parte in e.get("loc", [])),
                "mensaje": e.get("msg", ""),
            }
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Solicitud inválida (datos o caracteres no permitidos).",
                "errores": errores,
            },
        )