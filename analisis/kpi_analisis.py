"""Análisis de datos del ERP con Pandas/Matplotlib (unidad VI: análisis de datos y SPC).

Lee DIRECTAMENTE la base PostgreSQL del ERP (tablas y la vista v_existencias), recalcula los KPI
de forma independiente a la aplicación y genera gráficos + CSV en analisis/salida/.

  Desde el host:      python analisis/kpi_analisis.py            (PGHOST=localhost, PGPORT=5433)
  Dentro de Docker:   docker compose exec web python analisis/kpi_analisis.py
"""
import os
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import psycopg  # noqa: E402

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

SALIDA = Path(__file__).resolve().parent / "salida"
SALIDA.mkdir(exist_ok=True)

conexion = psycopg.connect(
    host=os.environ.get("POSTGRES_HOST", os.environ.get("PGHOST", "localhost")),
    port=os.environ.get("POSTGRES_PORT", os.environ.get("PGPORT", "5433" if "POSTGRES_HOST" not in os.environ else "5432")),
    dbname=os.environ.get("POSTGRES_DB", "erp"),
    user=os.environ.get("POSTGRES_USER", "erp"),
    password=os.environ.get("POSTGRES_PASSWORD", "erp"),
)


def q(sql):
    return pd.read_sql(sql, conexion)


# ---------- Datos -------------------------------------------------------------------------
ordenes = q("""
    SELECT o.numero, p.codigo AS producto, p.tipo, p.linea, o.cantidad_planificada::float AS planificada,
           o.cantidad_producida::float AS producida, o.fecha_inicio, o.fecha_fin,
           o.costo_material::float + o.costo_conversion::float AS costo_total, o.lote_id
    FROM produccion_ordenproduccion o JOIN maestros_producto p ON p.id = o.producto_id
    WHERE o.estado = 'TER'
""")
registros = q("""
    SELECT r.orden_id, c.codigo AS centro, EXTRACT(EPOCH FROM (r.fin - r.inicio))/60 AS minutos,
           r.tiempo_paro_min::float AS paro, op.tiempo_estandar_min::float * o.cantidad_planificada::float / ru.cantidad_lote::float AS estandar
    FROM produccion_registrooperacion r
    JOIN ingenieria_operacion op ON op.id = r.operacion_id
    JOIN ingenieria_ruta ru ON ru.id = op.ruta_id
    JOIN maestros_centrotrabajo c ON c.id = op.centro_id
    JOIN produccion_ordenproduccion o ON o.id = r.orden_id
    WHERE r.estado = 'TER' AND o.estado = 'TER'
""")
scrap = q("SELECT lote_id, SUM(cantidad_scrap)::float AS scrap FROM calidad_noconformidad GROUP BY lote_id")
existencias = q("""
    SELECT p.codigo, p.tipo, a.codigo AS almacen, v.saldo::float AS saldo, l.costo_unitario::float AS costo
    FROM v_existencias v JOIN maestros_producto p ON p.id = v.producto_id
    JOIN maestros_almacen a ON a.id = v.almacen_id LEFT JOIN inventario_lote l ON l.id = v.lote_id
""")
ventas = q("""
    SELECT m.fecha, p.codigo, m.cantidad::float AS cantidad, m.cantidad::float * m.costo_unitario::float AS costo
    FROM inventario_movimiento m JOIN maestros_producto p ON p.id = m.producto_id WHERE m.tipo = 'SVEN'
""")
ph = q("""
    SELECT i.fecha, p.codigo AS producto, r.valor::float AS ph, pc.minimo::float AS lie, pc.maximo::float AS lse
    FROM calidad_resultadoinspeccion r
    JOIN calidad_parametrocalidad pc ON pc.id = r.parametro_id
    JOIN calidad_inspeccion i ON i.id = r.inspeccion_id
    JOIN inventario_lote l ON l.id = i.lote_id JOIN maestros_producto p ON p.id = l.producto_id
    WHERE pc.nombre = 'pH' AND p.codigo = 'PT-DES1L' ORDER BY i.fecha
""")
telemetria = q("""
    SELECT l.fecha, s.codigo AS sensor, l.valor FROM iiot_lectura l JOIN iiot_sensor s ON s.id = l.sensor_id
    WHERE s.codigo = 'REA1-TEMP' ORDER BY l.fecha
""")

# ---------- KPI ---------------------------------------------------------------------------
ordenes = ordenes.merge(scrap, on="lote_id", how="left").fillna({"scrap": 0})
ordenes["buenas"] = ordenes["producida"] - ordenes["scrap"]
disponibilidad = (registros.minutos.sum() - registros.paro.sum()) / registros.minutos.sum()
rendimiento = min(registros.estandar.sum() / (registros.minutos.sum() - registros.paro.sum()), 1)
calidad = ordenes.buenas.sum() / ordenes.producida.sum()
oee = disponibilidad * rendimiento * calidad
yield_ = ordenes.buenas.sum() / ordenes.planificada.sum()
pt = ordenes[ordenes.tipo == "PT"]
costo_unitario = pt.costo_total.sum() / pt.producida.sum()
inventario_pt = (existencias[existencias.almacen == "ALM-PT"].saldo * existencias[existencias.almacen == "ALM-PT"].costo).sum()

kpi = pd.DataFrame([
    ("OEE", oee), ("Disponibilidad", disponibilidad), ("Rendimiento", rendimiento), ("Calidad", calidad),
    ("Yield", yield_), ("Costo unitario PT (C$)", costo_unitario), ("Inventario PT valorizado (C$)", inventario_pt),
    ("Costo de ventas acumulado (C$)", ventas.costo.sum()),
], columns=["indicador", "valor"])
kpi.to_csv(SALIDA / "kpi_pandas.csv", index=False)
print(kpi.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))

por_centro = registros.groupby("centro").agg(minutos=("minutos", "sum"), paro=("paro", "sum"), estandar=("estandar", "sum"))
por_centro["disponibilidad"] = (por_centro.minutos - por_centro.paro) / por_centro.minutos
por_centro["rendimiento"] = (por_centro.estandar / (por_centro.minutos - por_centro.paro)).clip(upper=1)
por_centro.to_csv(SALIDA / "oee_por_centro.csv")

# ---------- Gráficos ----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 3.6))
componentes = [disponibilidad, rendimiento, calidad, oee]
ax.bar(["Disponibilidad", "Rendimiento", "Calidad", "OEE"], [v * 100 for v in componentes], color=["#0f766e", "#0f766e", "#0f766e", "#d97706"])
ax.axhline(85, ls="--", color="gray", lw=1)
ax.text(3.45, 86, "clase mundial 85 %", fontsize=8, ha="right", color="gray")
ax.set_ylim(0, 105); ax.set_ylabel("%"); ax.set_title("OEE de la planta y sus componentes")
for i, v in enumerate(componentes):
    ax.text(i, v * 100 + 1.5, f"{v:.1%}", ha="center", fontsize=9)
fig.tight_layout(); fig.savefig(SALIDA / "oee.png", dpi=150)

# Carta de control individual (I-MR) del pH del desinfectante — SPC
if len(ph) >= 5:
    x = ph.ph
    mr = x.diff().abs()
    centro, sigma = x.mean(), mr.mean() / 1.128
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(range(1, len(x) + 1), x, marker="o", color="#0f766e")
    for valor, estilo, texto in [(centro, "-", "media"), (centro + 3 * sigma, "--", "LSC"), (centro - 3 * sigma, "--", "LIC")]:
        ax.axhline(valor, ls=estilo, color="#2563eb", lw=1); ax.text(len(x) + .2, valor, f"{texto} {valor:.2f}", fontsize=8, va="center")
    ax.axhspan(ph.lie.iloc[0], ph.lse.iloc[0], color="#10b981", alpha=.08, label="especificación 6.5–7.5")
    fuera = x[(x < ph.lie.iloc[0]) | (x > ph.lse.iloc[0])]
    ax.scatter(fuera.index + 1, fuera, color="#dc2626", zorder=3, label="fuera de especificación")
    ax.set_xlabel("inspección #"); ax.set_ylabel("pH"); ax.set_title("Carta de control I del pH — Desinfectante aromático")
    ax.legend(fontsize=8, loc="upper left"); fig.tight_layout(rect=(0, 0, 0.88, 1)); fig.savefig(SALIDA / "spc_ph_desinfectante.png", dpi=150)
    print(f"\nSPC pH: media={centro:.3f}  sigma={sigma:.3f}  LSC={centro + 3 * sigma:.2f}  LIC={centro - 3 * sigma:.2f}  "
          f"Cpk={min(ph.lse.iloc[0] - centro, centro - ph.lie.iloc[0]) / (3 * sigma):.2f}")

# Temperatura del reactor (IIoT) con límite de alarma
if not telemetria.empty:
    t = telemetria.tail(300)
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(pd.to_datetime(t.fecha), t.valor, lw=1, color="#0f766e")
    ax.axhline(88, ls="--", color="#dc2626", lw=1, label="alarma 88 °C")
    ax.set_title("Temperatura del reactor R-01 (lecturas IIoT)"); ax.set_ylabel("°C"); ax.legend(fontsize=8)
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(SALIDA / "iiot_temperatura_reactor.png", dpi=150)

print(f"\nArchivos generados en {SALIDA}")
