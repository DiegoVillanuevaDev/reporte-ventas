"""Pruebas del generador de reportes. Ejecutar con:  python -m unittest -v"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import load_workbook

from crear_bd_demo import crear_bd
from reporte.correo import construir_mensaje, enviar_reporte
from reporte.dashboard import generar_dashboard
from reporte.excel import generar_excel
from reporte.extraccion import obtener_ventas, rango_disponible
from reporte.resumen import calcular


class TestReporte(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.url = f"sqlite:///{cls.dir / 'prueba.db'}"
        crear_bd(cls.url)
        cls.desde, cls.hasta = rango_disponible(cls.url)
        cls.ventas = obtener_ventas(cls.url, cls.desde, cls.hasta)
        cls.res = calcular(cls.ventas)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_totales_coinciden_con_el_reporte_original(self):
        self.assertEqual(len(self.ventas), 461)
        self.assertEqual(self.res.total, Decimal("107817.05"))
        self.assertEqual(self.res.unidades, 1370)
        self.assertEqual(self.res.ticket_promedio, Decimal("233.88"))

    def test_filtro_por_fechas_incluye_ambos_extremos(self):
        junio = obtener_ventas(self.url, date(2026, 6, 1), date(2026, 6, 30))
        self.assertTrue(all(v.fecha.month == 6 for v in junio))
        self.assertEqual(calcular(junio).total, Decimal("33156.32"))

    def test_excel_usa_tabla_y_formulas_que_crecen_con_los_datos(self):
        ruta = generar_excel(self.ventas, self.res, self.desde, self.hasta, self.dir / "r.xlsx")
        wb = load_workbook(ruta)
        tabla = wb["Datos"].tables["Ventas"]
        self.assertEqual(tabla.ref, "A1:G462")
        encabezados = [c.value for c in wb["Datos"][1]]
        self.assertEqual([col.name for col in tabla.tableColumns], encabezados)
        self.assertIsNotNone(tabla.tableColumns[-1].calculatedColumnFormula)

        formulas = [c.value for fila in wb["Resumen"].iter_rows() for c in fila
                    if isinstance(c.value, str) and c.value.startswith("=")]
        self.assertIn("=SUM(Ventas[Total])", formulas)
        # Ningún rango fijo tipo $G$2:$G$462 ni TEXT(), que falla en Excel en español.
        self.assertFalse(any("$462" in f or "TEXT(" in f for f in formulas))

    def test_dashboard_se_genera(self):
        ruta = generar_dashboard(self.res, self.desde, self.hasta, self.dir / "d.png")
        self.assertGreater(ruta.stat().st_size, 50_000)

    def test_correo_lleva_dashboard_y_excel(self):
        excel = generar_excel(self.ventas, self.res, self.desde, self.hasta, self.dir / "c.xlsx")
        png = generar_dashboard(self.res, self.desde, self.hasta, self.dir / "c.png")
        entorno = {"SMTP_HOST": "smtp.prueba.local", "SMTP_USUARIO": "yo@prueba.local",
                   "SMTP_CONTRASENA": "x", "CORREO_DESTINO": "jefe@prueba.local, socio@prueba.local"}
        with mock.patch.dict(os.environ, entorno):
            msg = construir_mensaje(self.res, self.desde, self.hasta, excel, png)
            self.assertEqual(msg["To"], "jefe@prueba.local, socio@prueba.local")
            adjuntos = [p.get_filename() for p in msg.iter_attachments()]
            self.assertEqual(adjuntos, ["c.xlsx"])
            imagenes = [p for p in msg.walk() if p.get_content_type() == "image/png"]
            self.assertEqual(len(imagenes), 1)

            with mock.patch("smtplib.SMTP") as smtp:
                enviar_reporte(self.res, self.desde, self.hasta, excel, png)
                servidor = smtp.return_value
                servidor.starttls.assert_called_once()
                servidor.login.assert_called_once_with("yo@prueba.local", "x")
                servidor.send_message.assert_called_once()

    def test_correo_sin_configurar_avisa_que_falta(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SMTP_HOST"):
                enviar_reporte(self.res, self.desde, self.hasta, Path("x.xlsx"), Path("x.png"))


if __name__ == "__main__":
    unittest.main()
