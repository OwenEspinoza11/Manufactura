# Guion de la demostración en vivo (20 min)

Antes de empezar: `docker compose up` (o `docker compose down -v && docker compose up --build` para partir de datos limpios).
Abrir http://localhost:8000. Tener en otra pestaña el *Monitoreo IIoT*. Plan B declarado: video de respaldo y SQLite local.

| Min | Quién | Usuario | Qué se muestra | Ruta en el sistema |
|---|---|---|---|---|
| 0–2 | Bricio | `bmorales` | Problema (AS-IS), alcance y arquitectura ISA-95; qué es real y qué es simulado | *Arquitectura ISA-95* |
| 2–5 | Owen | `oespinoza` | **Compra → recepción**: recibir la OC pendiente de químicos (sus lotes quedan liberados) y la de aceite usado (queda **en cuarentena**) | *Compras* → OC confirmada → *Registrar recepción* |
| 5–7 | Ashly | `asalazar` | **Inspección de recepción** del aceite: acidez 2,1 → aprobado y liberado | *Inspecciones* → lote en espera |
| 7–11 | Kevin | `kperyman` | **Producción**: confirmar e iniciar la orden de *Base desinfectante* (emite materiales por lote FEFO); iniciar/terminar OP-10 y OP-20 registrando un paro; terminar la orden. Luego crear e iniciar la orden del *Desinfectante 1 L* | *Producción (MES)* |
| 11–12 | Kevin | `kperyman` | **IIoT en vivo**: el panel muestra el tanque T-01 ligado a la orden en curso; forzar una alarma con `docker compose exec web python iot/simulador_esp32.py --pico` | *Monitoreo IIoT* |
| 12–15 | Ashly | `asalazar` | **Lote y no conformidad en vivo**: inspección final del lote con pH 7,9 → NC automática → disposición *retrabajo* → consumo de ácido cítrico → reinspección pH 7,2 → lote liberado | *Inspecciones* → *No conformidades* |
| 15–17 | Amaru | `azamora` | **Venta y despacho**: confirmar y despachar el pedido en borrador (salida FEFO de lotes liberados). Mostrar la **trazabilidad** del lote despachado: hacia atrás hasta el proveedor y hacia adelante hasta el cliente | *Ventas* → *Lotes y trazabilidad* |
| 17–19 | Amaru | `azamora` | **KPI**: OEE (D×R×C), yield, FPY, rotación, costo real vs. estándar, litros de aceite reciclado; validación cruzada con Pandas y carta SPC del pH | *Indicadores KPI*, `analisis/kpi_analisis.py` |
| 19–20 | Dylan | `ddavila` | Patrones de diseño y por qué el inventario es un libro mayor inmutable (kardex); limitaciones declaradas | *Kardex*, `docs/problemas.md` |

Preguntas que conviene tener preparadas:
- ¿Dónde nace y dónde muere el costo unitario? (precio de la OC → consumo por lote → minutos reales × C$/h → lote → costo de ventas → rotación)
- ¿Por qué el OEE no es 100 %? (paros registrados, operaciones más lentas que el estándar, lote de base jabonosa enviado a scrap)
- ¿Qué pasa si se intenta producir con aceite en cuarentena? (el sistema lo impide: solo consume lotes liberados)
- ¿Qué cambia si mañana hay un PLC real? (solo el adaptador del nivel 2; la API del ERP no cambia)
