"""Configuración compartida: lee el archivo .env (si existe) sin dependencias extra."""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Colores de marca del reporte (mismos tonos que la versión original).
AZUL = "2E5597"
AZUL_CLARO = "7FA6E0"
GRIS_FONDO = "F2F2F2"
GRIS_TEXTO = "595959"


def cargar_env(ruta: Path = RAIZ / ".env") -> None:
    """Carga variables CLAVE=valor de un archivo .env sin pisar las ya definidas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def url_bd_por_defecto() -> str:
    """URL de conexión: la variable DB_URL o, si no existe, la base SQLite de demostración."""
    return os.environ.get("DB_URL", f"sqlite:///{RAIZ / 'ventas_demo.db'}")
