# Automatización de Reportes de Ventas

**Python + SQL + Excel** · De la base de datos a un reporte listo para el dueño del negocio, con un solo comando.

![Dashboard generado automáticamente](docs/dashboard_ejemplo.png)
📥 [Descarga el Excel de ejemplo](docs/reporte_ventas_ejemplo.xlsx)

## El problema

Muchos negocios registran sus ventas en una base de datos, pero cada semana o cada mes alguien tiene que exportar los datos, sumarlos por categoría y por vendedor, y armar un resumen en Excel. Es repetitivo, propenso a errores de cálculo y consume horas.

## La solución

Un script en Python que hace todo el proceso de principio a fin:

1. **Extracción:** se conecta a la base de datos y obtiene las ventas del período con una consulta SQL.
2. **Reporte en Excel:** genera un `.xlsx` con indicadores clave, ventas por categoría y por vendedor, tendencia mensual, top de productos y gráficos nativos de Excel.
3. **Dashboard en imagen:** produce un PNG listo para enviar por correo o WhatsApp, sin que nadie tenga que abrir un archivo.
4. **Envío automático (opcional):** manda el reporte por correo y se puede programar para que corra solo cada semana.

El Excel usa **fórmulas reales**, no valores fijos: si el cliente agrega ventas a la tabla, el resumen y los gráficos se recalculan solos.

## Resultado

| Antes | Después |
| --- | --- |
| ~1 hora de trabajo manual por reporte | Menos de 1 segundo con un solo comando (461 ventas de prueba) |
| Riesgo de errores de cálculo | Cálculos verificados con pruebas automáticas |
| Formato distinto en cada reporte | Formato profesional y uniforme |
| Alguien tiene que acordarse de hacerlo | Se genera y se envía solo cada semana |

## Qué cambió en la versión 2

| Problema en la versión 1 | Cómo se resolvió |
| --- | --- |
| Las fórmulas tenían rangos fijos (`$G$2:$G$462`): si se agregaban ventas, el resumen no cambiaba | Los datos están en una **Tabla de Excel** (`Ventas`) y las fórmulas usan referencias estructuradas (`=SUM(Ventas[Total])`), que crecen con los datos |
| La columna Mes usaba `TEXT(fecha,"yyyy-mm")`, que falla en Excel en español | La tendencia mensual filtra por rango de fechas (`SUMIFS` + `EDATE`), que funciona en cualquier idioma |
| Si aparecía una categoría o un vendedor nuevo, se perdía sin aviso | Filas de **control** que muestran cuánto dinero no está en el resumen (debe ser $0.00) |
| Solo MySQL, PostgreSQL y SQLite | También **SQL Server**, gracias a SQLAlchemy |
| El envío semanal solo se mencionaba | Envío por correo implementado (`--enviar`) y guía para programarlo |
| Etiquetas cortadas, porcentajes encimados en la dona y textos sin tildes | Dashboard rediseñado: la dona se reemplazó por el % en cada barra y un **Top 5 de productos** |

## Instalación

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (en macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

## Uso rápido (con datos de demostración)

```bash
python crear_bd_demo.py         # crea ventas_demo.db con 461 ventas (mayo–julio 2026)
python generar_reporte.py       # genera el Excel y el dashboard en la carpeta salida/
```

Más opciones:

```bash
python generar_reporte.py --desde 2026-06-01 --hasta 2026-06-30   # un período específico
python generar_reporte.py --ultimos-dias 7                        # la última semana
python generar_reporte.py --ultimos-dias 7 --enviar               # y enviarlo por correo
```

## Conectarlo a la base de datos real

Copia `.env.example` como `.env` y cambia `DB_URL`. La tabla debe llamarse `ventas` y tener las columnas `fecha, producto, categoria, cantidad, precio_unitario, vendedor` (si el cliente usa otros nombres, solo se ajusta la consulta en `reporte/extraccion.py`).

| Motor | `DB_URL` de ejemplo | Paquete extra |
| --- | --- | --- |
| SQLite | `sqlite:///ventas.db` | — |
| SQL Server | `mssql+pyodbc://usuario:clave@localhost:1433/VentasDB?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes` | `pyodbc` + ODBC Driver 18 |
| MySQL | `mysql+pymysql://usuario:clave@localhost:3306/ventas` | `pymysql` |
| PostgreSQL | `postgresql+psycopg2://usuario:clave@localhost:5432/ventas` | `psycopg2-binary` |

Para probar con SQL Server, crea primero la base `VentasDB` y luego carga los datos de demostración con `python crear_bd_demo.py --db-url "<tu DB_URL>"`.

## Envío por correo

Completa la sección de correo del `.env`. Ejemplo con Gmail: activa la verificación en dos pasos y crea una **contraseña de aplicación** (la contraseña normal no funciona por SMTP).

```
SMTP_HOST=smtp.gmail.com
SMTP_PUERTO=587
SMTP_USUARIO=tu_correo@gmail.com
SMTP_CONTRASENA=tu_contraseña_de_aplicación
CORREO_DESTINO=dueño@negocio.com, gerente@negocio.com
```

El correo lleva el resumen en el cuerpo, el dashboard incrustado y el Excel adjunto.

## Programarlo para que corra solo

**Windows (Programador de tareas):** ejecuta este comando una vez, desde la carpeta del proyecto. Genera y envía el reporte todos los lunes a las 7:00 a. m.

```bat
schtasks /Create /TN "Reporte semanal de ventas" /SC WEEKLY /D MON /ST 07:00 /TR "\"%CD%\ejecutar_reporte_semanal.bat\""
```

**Linux / macOS (cron):**

```
0 7 * * 1  cd /ruta/al/proyecto && .venv/bin/python generar_reporte.py --ultimos-dias 7 --enviar
```

## Pruebas

```bash
python -m unittest discover -s tests -t .
```

Verifican que los totales coinciden con el reporte original, que el filtro de fechas incluye ambos extremos, que el Excel usa la Tabla y no rangos fijos, y que el correo lleva el dashboard y el Excel (con un servidor SMTP simulado).

## Estructura

```
crear_bd_demo.py          crea la tabla y carga los datos de demostración
generar_reporte.py        punto de entrada (línea de comandos)
ejecutar_reporte_semanal.bat
reporte/
  extraccion.py           consulta SQL y modelo de la tabla
  resumen.py              cálculos en Python (dashboard y correo)
  excel.py                Excel con Tabla, fórmulas y gráficos
  dashboard.py            imagen PNG con matplotlib
  correo.py               envío por SMTP
  config.py               lectura del .env y colores
datos/ventas_demo.csv     461 ventas ficticias
tests/                    pruebas automáticas
```

---

Proyecto de muestra con datos ficticios para demostrar capacidades técnicas. La misma lógica se adapta a inventario, cuentas por cobrar, gastos o rendimiento por sucursal: solo cambian la conexión y las métricas.
