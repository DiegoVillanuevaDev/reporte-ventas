"""Crea la tabla `ventas` y la llena con los datos de demostración (461 ventas, mayo–julio 2026).

Funciona con cualquier motor compatible con SQLAlchemy:

    python crear_bd_demo.py                                       # SQLite local (ventas_demo.db)
    python crear_bd_demo.py --db-url "mssql+pyodbc://..."         # SQL Server
    python crear_bd_demo.py --db-url "mysql+pymysql://..."        # MySQL
    python crear_bd_demo.py --db-url "postgresql+psycopg2://..."  # PostgreSQL
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, insert

from reporte.config import RAIZ, cargar_env, url_bd_por_defecto
from reporte.extraccion import metadata, tabla_ventas

CSV_DEMO = RAIZ / "datos" / "ventas_demo.csv"


def leer_csv(ruta: Path = CSV_DEMO) -> list[dict]:
    with ruta.open(encoding="utf-8", newline="") as f:
        return [
            {
                "fecha": date.fromisoformat(fila["fecha"]),
                "producto": fila["producto"],
                "categoria": fila["categoria"],
                "cantidad": int(fila["cantidad"]),
                "precio_unitario": Decimal(fila["precio_unitario"]),
                "vendedor": fila["vendedor"],
            }
            for fila in csv.DictReader(f)
        ]


def crear_bd(db_url: str, ruta_csv: Path = CSV_DEMO) -> int:
    """Crea (o recrea) la tabla `ventas` y carga el CSV. Devuelve cuántas filas cargó."""
    engine = create_engine(db_url)
    metadata.drop_all(engine, tables=[tabla_ventas])
    metadata.create_all(engine, tables=[tabla_ventas])
    filas = leer_csv(ruta_csv)
    with engine.begin() as conn:
        conn.execute(insert(tabla_ventas), filas)
    engine.dispose()
    return len(filas)


def main() -> None:
    cargar_env()
    parser = argparse.ArgumentParser(description="Crea la base de datos de demostración.")
    parser.add_argument("--db-url", default=url_bd_por_defecto(),
                        help="URL de conexión de SQLAlchemy (por defecto: SQLite local)")
    args = parser.parse_args()

    n = crear_bd(args.db_url)
    destino = args.db_url.split("@")[-1]  # no imprime usuario ni contraseña
    print(f"Base de demostración lista: {n} ventas cargadas en {destino}")


if __name__ == "__main__":
    main()
