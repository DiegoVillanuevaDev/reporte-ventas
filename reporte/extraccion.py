"""Extracción de las ventas desde la base de datos con SQL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import (Column, Date, Integer, MetaData, Numeric, String,
                        Table, bindparam, create_engine, text)

# Definición de la tabla (la usa crear_bd_demo.py para crearla en cualquier motor).
metadata = MetaData()
tabla_ventas = Table(
    "ventas",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fecha", Date, nullable=False),
    Column("producto", String(100), nullable=False),
    Column("categoria", String(50), nullable=False),
    Column("cantidad", Integer, nullable=False),
    Column("precio_unitario", Numeric(10, 2), nullable=False),
    Column("vendedor", String(100), nullable=False),
)

# SQL estándar: funciona igual en SQLite, MySQL, PostgreSQL y SQL Server.
CONSULTA_VENTAS = (
    text(
        """
        SELECT fecha, producto, categoria, cantidad, precio_unitario, vendedor
        FROM ventas
        WHERE fecha >= :desde AND fecha < :hasta
        ORDER BY fecha, id
        """
    )
    .bindparams(bindparam("desde", type_=Date), bindparam("hasta", type_=Date))
    .columns(fecha=Date, cantidad=Integer, precio_unitario=Numeric(10, 2))
)

CONSULTA_RANGO = text("SELECT MIN(fecha), MAX(fecha) FROM ventas").columns()


@dataclass(frozen=True)
class Venta:
    fecha: date
    producto: str
    categoria: str
    cantidad: int
    precio_unitario: Decimal
    vendedor: str

    @property
    def total(self) -> Decimal:
        return self.cantidad * self.precio_unitario


def _a_fecha(valor) -> date:
    """Normaliza lo que devuelve cada motor (date, datetime o texto ISO)."""
    if isinstance(valor, date):
        return valor if type(valor) is date else valor.date()
    return date.fromisoformat(str(valor)[:10])


def rango_disponible(db_url: str) -> tuple[date, date] | None:
    """Primera y última fecha con ventas registradas, o None si la tabla está vacía."""
    engine = create_engine(db_url)
    with engine.connect() as conn:
        minimo, maximo = conn.execute(CONSULTA_RANGO).one()
    engine.dispose()
    if minimo is None:
        return None
    return _a_fecha(minimo), _a_fecha(maximo)


def obtener_ventas(db_url: str, desde: date, hasta: date) -> list[Venta]:
    """Ventas entre `desde` y `hasta`, ambos incluidos."""
    engine = create_engine(db_url)
    with engine.connect() as conn:
        filas = conn.execute(
            CONSULTA_VENTAS, {"desde": desde, "hasta": hasta + timedelta(days=1)}
        ).all()
    engine.dispose()
    return [
        Venta(
            fecha=_a_fecha(f.fecha),
            producto=f.producto,
            categoria=f.categoria,
            cantidad=int(f.cantidad),
            precio_unitario=Decimal(str(f.precio_unitario)).quantize(Decimal("0.01")),
            vendedor=f.vendedor,
        )
        for f in filas
    ]
