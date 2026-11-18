"""Genera el reporte de ventas: SQL → Excel con fórmulas + dashboard PNG (+ correo opcional).

Ejemplos:
    python generar_reporte.py                              # todo el historial
    python generar_reporte.py --desde 2026-06-01 --hasta 2026-06-30
    python generar_reporte.py --ultimos-dias 7 --enviar    # semanal, enviado por correo
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from reporte.config import RAIZ, cargar_env, url_bd_por_defecto
from reporte.correo import enviar_reporte
from reporte.dashboard import generar_dashboard
from reporte.excel import generar_excel
from reporte.extraccion import obtener_ventas, rango_disponible
from reporte.resumen import calcular


def _fecha(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Fecha inválida: {texto!r}. Usa el formato AAAA-MM-DD.")


def _argumentos() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Genera el reporte de ventas en Excel y como dashboard PNG.")
    p.add_argument("--db-url", default=url_bd_por_defecto(), help="URL de conexión de SQLAlchemy")
    p.add_argument("--desde", type=_fecha, help="Fecha inicial, AAAA-MM-DD (incluida)")
    p.add_argument("--hasta", type=_fecha, help="Fecha final, AAAA-MM-DD (incluida)")
    p.add_argument("--ultimos-dias", type=int, help="Reporta los últimos N días hasta hoy")
    p.add_argument("--salida", type=Path, default=RAIZ / "salida", help="Carpeta donde se guardan los archivos")
    p.add_argument("--enviar", action="store_true", help="Envía el reporte por correo (configurado en .env)")
    return p.parse_args()


def _periodo(args: argparse.Namespace) -> tuple[date, date] | None:
    if args.ultimos_dias:
        hasta = date.today()
        return hasta - timedelta(days=args.ultimos_dias - 1), hasta
    if args.desde and args.hasta:
        return args.desde, args.hasta
    rango = rango_disponible(args.db_url)
    if rango is None:
        return None
    return args.desde or rango[0], args.hasta or rango[1]


def main() -> int:
    cargar_env()
    args = _argumentos()
    inicio = time.perf_counter()

    periodo = _periodo(args)
    if periodo is None:
        print("La tabla de ventas está vacía: no hay nada que reportar.")
        return 1
    desde, hasta = periodo
    if desde > hasta:
        print("La fecha inicial es posterior a la final.")
        return 2

    print(f"1/3 Extrayendo ventas del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}...")
    ventas = obtener_ventas(args.db_url, desde, hasta)
    if not ventas:
        print("No hay ventas en ese período. No se generó ningún archivo.")
        return 1
    resumen = calcular(ventas)

    sufijo = f"{desde:%Y%m%d}_{hasta:%Y%m%d}"
    print(f"2/3 Generando Excel y dashboard ({len(ventas)} ventas)...")
    excel = generar_excel(ventas, resumen, desde, hasta, args.salida / f"reporte_ventas_{sufijo}.xlsx")
    dashboard = generar_dashboard(resumen, desde, hasta, args.salida / f"dashboard_ventas_{sufijo}.png")

    if args.enviar:
        print("3/3 Enviando por correo...")
        try:
            enviar_reporte(resumen, desde, hasta, excel, dashboard)
        except Exception as error:  # el reporte ya existe; solo falló el envío
            print(f"   No se pudo enviar el correo: {error}")
            return 3
    else:
        print("3/3 Envío por correo omitido (usa --enviar para activarlo).")

    print(f"\nListo en {time.perf_counter() - inicio:.1f} s")
    print(f"  Excel:     {excel}")
    print(f"  Dashboard: {dashboard}")
    print(f"  Ventas totales: ${resumen.total:,.2f}  ·  Transacciones: {resumen.transacciones}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
