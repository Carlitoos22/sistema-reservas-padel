from fastapi.templating import Jinja2Templates

# Instancia unica de plantillas Jinja2, compartida por todas las rutas.
# Busca los .html en la carpeta "templates/" (en la raiz del proyecto).
templates = Jinja2Templates(directory="templates")