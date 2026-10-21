# Evidencias técnicas

## Generadas automáticamente
- `analisis/`: salida de `analisis/kpi_analisis.py`, que lee PostgreSQL directamente:
  - `kpi_pandas.csv`: KPI recalculados fuera de la aplicación (validación cruzada con el tablero)
  - `oee.png`: OEE y sus componentes
  - `spc_ph_desinfectante.png`: carta de control I del pH con límites y Cpk
  - `iiot_temperatura_reactor.png`: telemetría del reactor con límite de alarma
  - `oee_por_centro.csv`
- Exportaciones CSV desde *Indicadores KPI → Exportar CSV* (movimientos, lotes, órdenes, KPI).

## Capturas a tomar y anotar para el informe (una por paso del flujo)
1. Tablero de inicio (KPI y alertas)
2. Orden de compra confirmada y su recepción con los lotes generados
3. Lote de aceite usado en cuarentena e inspección de recepción
4. Orden de producción: requerimiento de materiales (explosión de BOM)
5. Orden de producción en proceso: operaciones con tiempos, paros y consumos por lote
6. Inspección rechazada, no conformidad y su disposición (scrap / retrabajo / liberación)
7. Pedido de venta despachado con lotes
8. Trazabilidad de un lote (hacia atrás y hacia adelante)
9. Kardex de movimientos
10. Monitoreo IIoT con una alerta y lecturas ligadas a la orden
11. Indicadores KPI
12. Terminal con `docker compose logs puente-mqtt` (flujo MQTT → ERP)
