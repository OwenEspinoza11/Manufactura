"""Vista SQL de existencias por producto/lote/almacén (suma del libro mayor).

Se consulta desde herramientas externas (pandas, Power BI) sin pasar por la aplicación.
SQL estándar: funciona en PostgreSQL y en SQLite.
"""
from django.db import migrations

CREAR = """
CREATE VIEW v_existencias AS
SELECT m.producto_id, m.lote_id, m.almacen_id, SUM(m.cantidad) AS saldo
FROM (
    SELECT producto_id, lote_id, almacen_destino_id AS almacen_id, cantidad
    FROM inventario_movimiento WHERE almacen_destino_id IS NOT NULL
    UNION ALL
    SELECT producto_id, lote_id, almacen_origen_id AS almacen_id, -cantidad
    FROM inventario_movimiento WHERE almacen_origen_id IS NOT NULL
) m
GROUP BY m.producto_id, m.lote_id, m.almacen_id
HAVING SUM(m.cantidad) <> 0;
"""

BORRAR = "DROP VIEW IF EXISTS v_existencias;"


class Migration(migrations.Migration):
    dependencies = [("inventario", "0001_initial")]
    operations = [migrations.RunSQL(CREAR, BORRAR)]
