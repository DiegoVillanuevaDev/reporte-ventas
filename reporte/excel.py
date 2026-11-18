"""Genera el reporte en Excel con fórmulas reales.

Decisiones clave:
- Los datos van en una Tabla de Excel llamada `Ventas`. Las fórmulas del resumen usan
  referencias estructuradas (`Ventas[Total]`), así que si el cliente agrega filas a la
  tabla, todo el resumen se recalcula solo.
- La tendencia mensual filtra por rango de fechas (SUMIFS + EDATE) en lugar de TEXT(),
  porque el formato de TEXT() cambia según el idioma de Excel y falla en Excel en español.
- Hay filas de control que avisan si aparece una categoría o un vendedor nuevo que no
  está en el resumen.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableColumn, TableFormula, TableStyleInfo

from .config import AZUL, GRIS_FONDO, GRIS_TEXTO
from .extraccion import Venta
from .resumen import Resumen

FMT_DINERO = '"$"#,##0.00'
FMT_ENTERO = "#,##0"
FMT_PCT = "0.0%"
FMT_VARIACION = '+0.0%;-0.0%;0.0%'
FMT_FECHA = "dd/mm/yyyy"
FMT_MES = "mmm yyyy"

ENCABEZADOS = ["Fecha", "Producto", "Categoría", "Cantidad", "Precio Unitario", "Vendedor", "Total"]
TOTAL_FILA = "Ventas[[#This Row],[Cantidad]]*Ventas[[#This Row],[Precio Unitario]]"

F_TITULO = Font(size=18, bold=True, color=AZUL)
F_SUBTITULO = Font(size=10, italic=True, color=GRIS_TEXTO)
F_SECCION = Font(size=13, bold=True, color=AZUL)
F_ENCABEZADO = Font(bold=True, color="FFFFFF")
F_KPI_VALOR = Font(size=16, bold=True, color=AZUL)
F_CONTROL = Font(size=9, italic=True, color=GRIS_TEXTO)
RELLENO_ENC = PatternFill("solid", fgColor=AZUL)
RELLENO_KPI = PatternFill("solid", fgColor=GRIS_FONDO)
BORDE_INF = Border(bottom=Side(style="thin", color="D9D9D9"))


def _hoja_datos(wb: Workbook, ventas: list[Venta]) -> None:
    ws = wb.active
    ws.title = "Datos"
    ws.append(ENCABEZADOS)
    for i, v in enumerate(ventas, start=2):
        ws.append([v.fecha, v.producto, v.categoria, v.cantidad, float(v.precio_unitario), v.vendedor,
                   f"={TOTAL_FILA}"])
        ws.cell(i, 1).number_format = FMT_FECHA
        ws.cell(i, 5).number_format = FMT_DINERO
        ws.cell(i, 7).number_format = FMT_DINERO

    ultima = len(ventas) + 1
    tabla = Table(displayName="Ventas", ref=f"A1:G{ultima}")
    tabla.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    # Los nombres de columna deben coincidir con los encabezados o Excel "repara" el archivo.
    tabla.tableColumns = [TableColumn(id=i, name=nombre) for i, nombre in enumerate(ENCABEZADOS, start=1)]
    # Columna calculada: Excel copia la fórmula sola en cada fila nueva que se agregue.
    tabla.tableColumns[-1].calculatedColumnFormula = TableFormula(attr_text=TOTAL_FILA)
    ws.add_table(tabla)

    ws.freeze_panes = "A2"
    for col, ancho in zip("ABCDEFG", [12, 24, 14, 10, 15, 18, 13]):
        ws.column_dimensions[col].width = ancho


def _encabezado_tabla(ws, fila: int, titulos: list[str]) -> None:
    for c, titulo in enumerate(titulos, start=1):
        celda = ws.cell(fila, c, titulo)
        celda.font = F_ENCABEZADO
        celda.fill = RELLENO_ENC
        celda.alignment = Alignment(horizontal="center" if c > 1 else "left")


def _seccion(ws, fila: int, titulo: str) -> None:
    ws.cell(fila, 1, titulo).font = F_SECCION


def _hoja_resumen(wb: Workbook, res: Resumen, desde: date, hasta: date) -> None:
    ws = wb.create_sheet("Resumen", 0)
    ws.sheet_view.showGridLines = False

    ws["A1"] = "Reporte de Ventas — Resumen Ejecutivo"
    ws["A1"].font = F_TITULO
    ws["A2"] = (f"Período: {desde:%d/%m/%Y} – {hasta:%d/%m/%Y}  ·  "
                f"Generado automáticamente desde la base de datos el {datetime.now():%d/%m/%Y %H:%M}")
    ws["A2"].font = F_SUBTITULO

    # --- Indicadores clave ---
    kpis = [
        ("Ventas totales", "=SUM(Ventas[Total])", FMT_DINERO),
        ("Unidades vendidas", "=SUM(Ventas[Cantidad])", FMT_ENTERO),
        ("Transacciones", "=COUNT(Ventas[Fecha])", FMT_ENTERO),
        ("Ticket promedio", "=IFERROR(B4/B6,0)", FMT_DINERO),
    ]
    for i, (etiqueta, formula, fmt) in enumerate(kpis, start=4):
        ws.cell(i, 1, etiqueta).fill = RELLENO_KPI
        valor = ws.cell(i, 2, formula)
        valor.number_format, valor.font, valor.fill = fmt, F_KPI_VALOR, RELLENO_KPI

    # --- Ventas por categoría ---
    fila = 9
    _seccion(ws, fila, "Ventas por categoría")
    _encabezado_tabla(ws, fila + 1, ["Categoría", "Total vendido", "Unidades", "% del total"])
    ini_cat = fila + 2
    for i, categoria in enumerate(res.por_categoria):
        r = ini_cat + i
        ws.cell(r, 1, categoria)
        ws.cell(r, 2, f"=SUMIFS(Ventas[Total],Ventas[Categoría],A{r})").number_format = FMT_DINERO
        ws.cell(r, 3, f"=SUMIFS(Ventas[Cantidad],Ventas[Categoría],A{r})").number_format = FMT_ENTERO
        ws.cell(r, 4, f"=IFERROR(B{r}/$B$4,0)").number_format = FMT_PCT
        for c in range(1, 5):
            ws.cell(r, c).border = BORDE_INF
    fin_cat = ini_cat + len(res.por_categoria) - 1
    control_cat = fin_cat + 1
    ws.cell(control_cat, 1, "Control: ventas en categorías no listadas").font = F_CONTROL
    c = ws.cell(control_cat, 2, f"=B4-SUM(B{ini_cat}:B{fin_cat})")
    c.number_format, c.font = FMT_DINERO, F_CONTROL

    # --- Ventas por vendedor ---
    fila = control_cat + 2
    _seccion(ws, fila, "Ventas por vendedor")
    _encabezado_tabla(ws, fila + 1, ["Vendedor", "Total vendido", "Transacciones", "Ticket promedio"])
    ini_ven = fila + 2
    for i, vendedor in enumerate(res.por_vendedor):
        r = ini_ven + i
        ws.cell(r, 1, vendedor)
        ws.cell(r, 2, f"=SUMIFS(Ventas[Total],Ventas[Vendedor],A{r})").number_format = FMT_DINERO
        ws.cell(r, 3, f"=COUNTIFS(Ventas[Vendedor],A{r})").number_format = FMT_ENTERO
        ws.cell(r, 4, f"=IFERROR(B{r}/C{r},0)").number_format = FMT_DINERO
        for c in range(1, 5):
            ws.cell(r, c).border = BORDE_INF
    fin_ven = ini_ven + len(res.por_vendedor) - 1
    control_ven = fin_ven + 1
    ws.cell(control_ven, 1, "Control: ventas de vendedores no listados").font = F_CONTROL
    c = ws.cell(control_ven, 2, f"=B4-SUM(B{ini_ven}:B{fin_ven})")
    c.number_format, c.font = FMT_DINERO, F_CONTROL

    # --- Tendencia mensual (por rango de fechas, funciona en cualquier idioma de Excel) ---
    fila = control_ven + 2
    _seccion(ws, fila, "Tendencia mensual")
    _encabezado_tabla(ws, fila + 1, ["Mes", "Total vendido", "Var. vs. mes anterior"])
    ini_mes = fila + 2
    for i, mes in enumerate(res.por_mes):
        r = ini_mes + i
        ws.cell(r, 1, mes).number_format = FMT_MES
        ws.cell(r, 1).alignment = Alignment(horizontal="left")
        ws.cell(r, 2, f'=SUMIFS(Ventas[Total],Ventas[Fecha],">="&A{r},Ventas[Fecha],"<"&EDATE(A{r},1))'
                ).number_format = FMT_DINERO
        if i == 0:
            ws.cell(r, 3, "—").alignment = Alignment(horizontal="center")
        else:
            ws.cell(r, 3, f"=IFERROR(B{r}/B{r - 1}-1,0)").number_format = FMT_VARIACION
        for col in range(1, 4):
            ws.cell(r, col).border = BORDE_INF
    fin_mes = ini_mes + len(res.por_mes) - 1

    # --- Top productos ---
    fila = fin_mes + 2
    _seccion(ws, fila, f"Top {len(res.top_productos)} productos")
    _encabezado_tabla(ws, fila + 1, ["Producto", "Total vendido", "Unidades"])
    ini_top = fila + 2
    for i, (producto, _, _) in enumerate(res.top_productos):
        r = ini_top + i
        ws.cell(r, 1, producto)
        ws.cell(r, 2, f"=SUMIFS(Ventas[Total],Ventas[Producto],A{r})").number_format = FMT_DINERO
        ws.cell(r, 3, f"=SUMIFS(Ventas[Cantidad],Ventas[Producto],A{r})").number_format = FMT_ENTERO
        for col in range(1, 4):
            ws.cell(r, col).border = BORDE_INF

    for col, ancho in zip("ABCD", [40, 18, 20, 18]):
        ws.column_dimensions[col].width = ancho

    # --- Gráficos nativos de Excel (se actualizan junto con las fórmulas) ---
    graf_cat = BarChart()
    graf_cat.type = "bar"
    graf_cat.title = "Ventas por categoría"
    graf_cat.add_data(Reference(ws, min_col=2, min_row=ini_cat - 1, max_row=fin_cat), titles_from_data=True)
    graf_cat.set_categories(Reference(ws, min_col=1, min_row=ini_cat, max_row=fin_cat))
    graf_cat.x_axis.scaling.orientation = "maxMin"  # la mayor arriba
    graf_cat.legend = None

    graf_mes = LineChart()
    graf_mes.title = "Tendencia mensual"
    graf_mes.add_data(Reference(ws, min_col=2, min_row=ini_mes - 1, max_row=fin_mes), titles_from_data=True)
    graf_mes.set_categories(Reference(ws, min_col=1, min_row=ini_mes, max_row=fin_mes))
    graf_mes.legend = None

    graf_ven = BarChart()
    graf_ven.title = "Ventas por vendedor"
    graf_ven.add_data(Reference(ws, min_col=2, min_row=ini_ven - 1, max_row=fin_ven), titles_from_data=True)
    graf_ven.set_categories(Reference(ws, min_col=1, min_row=ini_ven, max_row=fin_ven))
    graf_ven.legend = None

    for graf, ancla in ((graf_cat, "F3"), (graf_mes, "F19"), (graf_ven, "F35")):
        graf.width, graf.height = 17, 7.5
        graf.y_axis.numFmt = '"$"#,##0'
        graf.y_axis.scaling.min = 0
        graf.x_axis.delete = False
        graf.y_axis.delete = False
        graf.y_axis.majorGridlines = None
        graf.dataLabels = DataLabelList()
        graf.dataLabels.showVal = True
        graf.dataLabels.showSerName = False
        graf.dataLabels.showCatName = False
        graf.dataLabels.showLegendKey = False
        graf.dataLabels.position = "t" if graf is graf_mes else "outEnd"
        graf.dataLabels.numFmt = '"$"#,##0'
        for serie in graf.series:
            serie.graphicalProperties.solidFill = AZUL
            serie.graphicalProperties.line.solidFill = AZUL
            serie.smooth = False
        ws.add_chart(graf, ancla)

    ws.print_options.horizontalCentered = True
    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1


def generar_excel(ventas: list[Venta], res: Resumen, desde: date, hasta: date, ruta: Path) -> Path:
    wb = Workbook()
    _hoja_datos(wb, ventas)
    _hoja_resumen(wb, res, desde, hasta)
    wb.active = 0
    ruta.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta)
    return ruta
