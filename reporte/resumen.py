"""Cálculos del resumen en Python (para el dashboard, el correo y para ordenar las tablas)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .extraccion import Venta


@dataclass
class Resumen:
    total: Decimal
    unidades: int
    transacciones: int
    por_categoria: dict[str, Decimal]
    por_vendedor: dict[str, Decimal]
    transacciones_por_vendedor: dict[str, int]
    por_mes: dict[date, Decimal]
    top_productos: list[tuple[str, Decimal, int]] = field(default_factory=list)

    @property
    def ticket_promedio(self) -> Decimal:
        if not self.transacciones:
            return Decimal("0")
        return (self.total / self.transacciones).quantize(Decimal("0.01"))


def _ordenar(d: dict) -> dict:
    return dict(sorted(d.items(), key=lambda kv: kv[1], reverse=True))


def calcular(ventas: list[Venta], top_n: int = 5) -> Resumen:
    por_categoria: dict[str, Decimal] = defaultdict(Decimal)
    por_vendedor: dict[str, Decimal] = defaultdict(Decimal)
    trans_vendedor: dict[str, int] = defaultdict(int)
    por_mes: dict[date, Decimal] = defaultdict(Decimal)
    por_producto: dict[str, Decimal] = defaultdict(Decimal)
    unidades_producto: dict[str, int] = defaultdict(int)

    for v in ventas:
        por_categoria[v.categoria] += v.total
        por_vendedor[v.vendedor] += v.total
        trans_vendedor[v.vendedor] += 1
        por_mes[v.fecha.replace(day=1)] += v.total
        por_producto[v.producto] += v.total
        unidades_producto[v.producto] += v.cantidad

    top = sorted(por_producto.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return Resumen(
        total=sum((v.total for v in ventas), Decimal("0")),
        unidades=sum(v.cantidad for v in ventas),
        transacciones=len(ventas),
        por_categoria=_ordenar(por_categoria),
        por_vendedor=_ordenar(por_vendedor),
        transacciones_por_vendedor=dict(trans_vendedor),
        por_mes=dict(sorted(por_mes.items())),
        top_productos=[(p, t, unidades_producto[p]) for p, t in top],
    )
