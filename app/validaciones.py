"""
Consigna 2 (Sanitización): detecta caracteres típicos de ataques.

- XSS:  < > " '   (para inyectar <script> o romper HTML)
- SQLi: ' ; -- /* */   (para inyectar SQL: '; DROP TABLE ...)

Si el texto trae alguno, se lanza un ValueError. Pydantic lo convierte en
un error de validación y, gracias a app/seguridad_http.py, la respuesta
sale como 400 Bad Request (limpio), nunca como 500 (crash).
"""
import re

# Caracteres / secuencias peligrosas
PATRON_PELIGROSO = re.compile(r"""[<>"'`;\\]|--|/\*|\*/""")


def validar_texto_seguro(valor):
    if valor is None:
        return valor
    if isinstance(valor, str) and PATRON_PELIGROSO.search(valor):
        raise ValueError("Contiene caracteres no permitidos")
    return valor