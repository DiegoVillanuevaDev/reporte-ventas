"""Dashboard en imagen (PNG) listo para enviar por correo o WhatsApp."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventana: funciona en servidores y tareas programadas
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from .config import AZUL, AZUL_CLARO, GRIS_FONDO, GRIS_TEXTO
from .resumen import Resumen

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
C_AZUL, C_AZUL_CLARO, C_GRIS, C_FONDO = f"#{AZUL}", f"#{AZUL_CLARO}", f"#{GRIS_TEXTO}", f"#{GRIS_FONDO}"
C_VERDE, C_ROJO = "#2E7D32", "#C62828"


def _dinero(x: float, decimales: int = 0) -> str:
    return f"${x:,.{decimales}f}"


def _limpiar_ejes(ax, eje_valores: str = "x") -> None:
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.spines["left" if eje_valores == "x" else "bottom"].set_color("#BFBFBF")
    ax.spines["bottom" if eje_valores == "x" else "left"].set_visible(False)
    ax.tick_params(colors=C_GRIS, labelsize=10)
    getattr(ax, f"{'x' if eje_valores == 'x' else 'y'}axis").set_visible(False)


def _barras_horizontales(ax, etiquetas: list[str], valores: list[float], titulo: str,
                         notas: list[str] | None = None) -> None:
    y = range(len(etiquetas))
    ax.barh(y, valores, color=C_AZUL, height=0.6)
    ax.set_yticks(list(y), etiquetas)
    ax.invert_yaxis()  # la mayor arriba
    maximo = max(valores) if valores else 1
    ax.set_xlim(0, maximo * 1.32)
    for i, valor in enumerate(valores):
        texto = _dinero(valor) + (f"  ({notas[i]})" if notas else "")
        ax.text(valor + maximo * 0.015, i, texto, va="center", fontsize=10, color="#262626")
    ax.set_title(titulo, loc="left", fontsize=13, fontweight="bold", color=C_AZUL, pad=10)
    _limpiar_ejes(ax, "x")


def generar_dashboard(res: Resumen, desde: date, hasta: date, ruta: Path) -> Path:
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig = plt.figure(figsize=(16, 10), dpi=110, facecolor="white")
    fila_kpis = fig.add_gridspec(1, 4, wspace=0.12, left=0.04, right=0.97, top=0.87, bottom=0.78)
    graficos = fig.add_gridspec(2, 2, wspace=0.42, hspace=0.42, left=0.11, right=0.97, top=0.69, bottom=0.05)

    periodo = f"{desde.day} {MESES[desde.month - 1]} {desde.year} – {hasta.day} {MESES[hasta.month - 1]} {hasta.year}"
    fig.text(0.04, 0.955, "Reporte de Ventas — Resumen Ejecutivo", fontsize=22, fontweight="bold", color=C_AZUL)
    fig.text(0.04, 0.92, f"Generado automáticamente desde la base de datos  ·  Período: {periodo}",
             fontsize=11, color=C_GRIS)

    # --- Indicadores clave ---
    total = float(res.total)
    kpis = [
        (_dinero(total, 2), "Ventas totales"),
        (f"{res.unidades:,}", "Unidades vendidas"),
        (f"{res.transacciones:,}", "Transacciones"),
        (_dinero(float(res.ticket_promedio), 2), "Ticket promedio"),
    ]
    for i, (valor, etiqueta) in enumerate(kpis):
        ax = fig.add_subplot(fila_kpis[0, i])
        ax.set_facecolor(C_FONDO)
        ax.set_xticks([]), ax.set_yticks([])
        for lado in ax.spines.values():
            lado.set_visible(False)
        ax.text(0.5, 0.6, valor, ha="center", va="center", fontsize=20, fontweight="bold", color=C_AZUL,
                transform=ax.transAxes)
        ax.text(0.5, 0.2, etiqueta, ha="center", va="center", fontsize=11, color=C_GRIS, transform=ax.transAxes)

    # --- Ventas por categoría (con su % del total: reemplaza la dona del original) ---
    ax = fig.add_subplot(graficos[0, 0])
    cats = list(res.por_categoria.items())
    _barras_horizontales(
        ax, [c for c, _ in cats], [float(v) for _, v in cats], "Ventas por categoría",
        [f"{float(v) / total:.0%}" if total else "0%" for _, v in cats],
    )

    # --- Tendencia mensual con variación % ---
    ax = fig.add_subplot(graficos[0, 1])
    meses = list(res.por_mes.items())
    etiquetas = [f"{MESES[m.month - 1]} {m.year}" for m, _ in meses]
    valores = [float(v) for _, v in meses]
    ax.plot(etiquetas, valores, color=C_AZUL, marker="o", linewidth=2.5, markersize=8)
    ax.fill_between(etiquetas, valores, color=C_AZUL, alpha=0.08)
    ax.set_ylim(0, max(valores) * 1.35 if valores else 1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: _dinero(x)))
    ax.grid(axis="y", color="#E7E7E7")
    for i, valor in enumerate(valores):
        ax.annotate(_dinero(valor), (i, valor), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=10, fontweight="bold", color="#262626")
        if i > 0 and valores[i - 1]:
            cambio = valor / valores[i - 1] - 1
            ax.annotate(f"{cambio:+.1%}", (i, valor), textcoords="offset points", xytext=(0, -20),
                        ha="center", fontsize=10, color=C_VERDE if cambio >= 0 else C_ROJO)
    if len(valores) == 1:
        ax.set_xlim(-0.5, 0.5)
    ax.set_title("Tendencia mensual", loc="left", fontsize=13, fontweight="bold", color=C_AZUL, pad=10)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(colors=C_GRIS, labelsize=10)

    # --- Ventas por vendedor ---
    ax = fig.add_subplot(graficos[1, 0])
    vendedores = list(res.por_vendedor.items())
    _barras_horizontales(
        ax, [n for n, _ in vendedores], [float(v) for _, v in vendedores], "Ventas por vendedor",
        [f"{res.transacciones_por_vendedor[n]} ventas" for n, _ in vendedores],
    )

    # --- Top productos (nuevo: dice qué vender, cosa que la dona no decía) ---
    ax = fig.add_subplot(graficos[1, 1])
    top = res.top_productos
    _barras_horizontales(
        ax, [p for p, _, _ in top], [float(t) for _, t, _ in top], f"Top {len(top)} productos",
        [f"{u} u." for _, _, u in top],
    )

    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, facecolor="white")
    plt.close(fig)
    return ruta
