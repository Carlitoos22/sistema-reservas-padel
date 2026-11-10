import io
import qrcode

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.plantillas import templates
from app.seguridad import usuario_actual
from app.controladores import controlador_reservas

# ===== COMPROBANTE DE RESERVA CON QR =====
# El jugador ve el comprobante de su reserva con un código QR.
# El QR apunta a /validar/{id}, una página pública que el dueño abre al
# escanearlo para confirmar que la reserva es válida.

router = APIRouter(tags=["Comprobante"])


@router.get("/reserva/{id_reserva}/comprobante", response_class=HTMLResponse)
def comprobante(request: Request, id_reserva: int, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if usuario is None:
        return RedirectResponse(url="/login", status_code=303)
    reserva = controlador_reservas.obtener_reserva(db, id_reserva)
    # Control de titularidad: solo el dueño de la reserva ve su comprobante
    if reserva is None or reserva.usuario_email != usuario.email:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return templates.TemplateResponse(
        request, "comprobante.html", {"usuario": usuario, "reserva": reserva}
    )


@router.get("/reserva/{id_reserva}/qr.png")
def qr_reserva(request: Request, id_reserva: int, db: Session = Depends(get_db)):
    usuario = usuario_actual(request, db)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Tenés que iniciar sesión.")
    reserva = controlador_reservas.obtener_reserva(db, id_reserva)
    if reserva is None or reserva.usuario_email != usuario.email:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    url_validacion = str(request.base_url).rstrip("/") + f"/validar/{id_reserva}"
    img = qrcode.make(url_validacion)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/png")


@router.get("/validar/{id_reserva}", response_class=HTMLResponse)
def validar(request: Request, id_reserva: int, db: Session = Depends(get_db)):
    """Página pública: se abre al escanear el QR. Muestra si la reserva es válida."""
    reserva = controlador_reservas.obtener_reserva(db, id_reserva)
    return templates.TemplateResponse(
        request, "validar.html", {"reserva": reserva}
    )
