"""Exporta el contrato OpenAPI del servicio a docs/openapi.json.

Uso (desde la carpeta canchas/):
  python -m scripts.exportar_openapi

No necesita la base ni Redis levantados: solo arma el esquema a partir de las rutas.
Con el servicio levantado también se puede bajar de http://localhost:8002/openapi.json
"""
import json
from pathlib import Path

from app.main import app

CARPETA_DOCS = Path(__file__).resolve().parents[2] / "docs"


def main():
    # Dentro del contenedor no está la carpeta docs/: en ese caso se deja en el directorio actual.
    DESTINO = CARPETA_DOCS / "openapi.json" if CARPETA_DOCS.is_dir() else Path("openapi.json")
    DESTINO.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Contrato exportado en {DESTINO}")


if __name__ == "__main__":
    main()
