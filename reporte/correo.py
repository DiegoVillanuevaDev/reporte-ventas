"""Envío del reporte por correo (SMTP). Configuración en el archivo .env."""

from __future__ import annotations

import os
import smtplib
import ssl
from datetime import date
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from .config import AZUL
from .resumen import Resumen

VARIABLES = ("SMTP_HOST", "SMTP_USUARIO", "SMTP_CONTRASENA", "CORREO_DESTINO")


def configuracion_faltante() -> list[str]:
    return [v for v in VARIABLES if not os.environ.get(v)]


def construir_mensaje(res: Resumen, desde: date, hasta: date, excel: Path, dashboard: Path) -> EmailMessage:
    remitente = os.environ.get("CORREO_REMITENTE") or os.environ["SMTP_USUARIO"]
    destinos = [d.strip() for d in os.environ["CORREO_DESTINO"].split(",") if d.strip()]

    msg = EmailMessage()
    msg["Subject"] = f"Reporte de ventas {desde:%d/%m/%Y} – {hasta:%d/%m/%Y}"
    msg["From"] = remitente
    msg["To"] = ", ".join(destinos)

    resumen_texto = (
        f"Ventas totales: ${res.total:,.2f}\n"
        f"Transacciones: {res.transacciones:,}\n"
        f"Ticket promedio: ${res.ticket_promedio:,.2f}\n"
    )
    msg.set_content(
        f"Hola,\n\nAdjunto el reporte de ventas del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}.\n\n"
        f"{resumen_texto}\nEl detalle completo está en el Excel adjunto.\n"
    )

    cid = make_msgid(domain="reporte.local")
    msg.add_alternative(
        f"""<html><body style="font-family:Arial,sans-serif;color:#262626">
        <p>Hola,</p>
        <p>Adjunto el reporte de ventas del <b>{desde:%d/%m/%Y}</b> al <b>{hasta:%d/%m/%Y}</b>.</p>
        <p style="font-size:15px">
          Ventas totales: <b style="color:#{AZUL}">${res.total:,.2f}</b> ·
          Transacciones: <b>{res.transacciones:,}</b> ·
          Ticket promedio: <b>${res.ticket_promedio:,.2f}</b>
        </p>
        <img src="cid:{cid[1:-1]}" style="max-width:100%" alt="Dashboard de ventas">
        <p>El detalle completo está en el Excel adjunto.</p>
        </body></html>""",
        subtype="html",
    )
    msg.get_payload()[1].add_related(dashboard.read_bytes(), "image", "png", cid=cid)

    msg.add_attachment(
        excel.read_bytes(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=excel.name,
    )
    return msg


def enviar_reporte(res: Resumen, desde: date, hasta: date, excel: Path, dashboard: Path) -> None:
    faltan = configuracion_faltante()
    if faltan:
        raise RuntimeError("Falta configurar en el archivo .env: " + ", ".join(faltan))

    msg = construir_mensaje(res, desde, hasta, excel, dashboard)
    host = os.environ["SMTP_HOST"]
    puerto = int(os.environ.get("SMTP_PUERTO", "587"))
    contexto = ssl.create_default_context()

    if puerto == 465:
        servidor = smtplib.SMTP_SSL(host, puerto, context=contexto, timeout=30)
    else:
        servidor = smtplib.SMTP(host, puerto, timeout=30)
        servidor.starttls(context=contexto)
    with servidor:
        servidor.login(os.environ["SMTP_USUARIO"], os.environ["SMTP_CONTRASENA"])
        servidor.send_message(msg)
