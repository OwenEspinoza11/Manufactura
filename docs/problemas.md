# Registro de problemas encontrados

| # | Fecha | Problema | Resolución | Estado |
|---|---|---|---|---|
| P-01 | 20/10/2026 | Odoo 17 Community no incluye el módulo *Quality*, necesario para registrar no conformidades con disposición. | Se cambió a desarrollo propio (Django + PostgreSQL), que la guía acepta. Ver cambio 1 en `cambios_entrega1.md`. | Resuelto |
| P-02 | 20/10/2026 | La BOM de la Entrega 1 no tenía cantidades en el nivel 2 ("según formulación validada"). | Se cargaron cantidades de prueba versionadas (BOM v1.0). Quedan editables en *Administración → BOM*. | Resuelto (requiere validación técnica) |
| P-03 | 20/10/2026 | Si el semielaborado rendía menos de lo planificado, la orden del producto terminado no tenía material suficiente y fallaba al iniciar. | La merma del semielaborado se modela en la BOM (`merma_pct`). El sistema valida el faltante antes de emitir materiales y lo informa por componente. | Resuelto |
| P-04 | 20/10/2026 | La rotación de inventario salía inflada (19×): el inventario inicial del periodo de 90 días era cero porque el historial empieza hace 6 semanas. | Periodo de 30 días e inventario promedio calculado con fotos semanales del inventario valorizado. | Resuelto |
| P-05 | 20/10/2026 | Las lecturas IIoT llegaban sin contexto de producción (no se sabía a qué lote correspondían). | Cada dispositivo pertenece a un centro de trabajo; la lectura se vincula a la orden con una operación en curso en ese centro y a su lote. | Resuelto |
| P-06 | 20/10/2026 | Se podía inspeccionar (y liberar) un lote cuya orden de producción seguía en proceso. | Regla de negocio: solo se inspecciona un lote producido cuando su orden está terminada. | Resuelto |
| P-07 | 20/10/2026 | Un retrabajo necesita consumir material correctivo (ácido cítrico) en una orden ya cerrada. | Se permite consumo adicional en una orden terminada si su lote está en retrabajo; el costo unitario del lote se recalcula. | Resuelto |
| P-08 | 20/10/2026 | La migración de la vista SQL `v_existencias` fallaba si se generaba antes que la migración inicial de inventario. | Se crea como migración `0002` dependiente de `0001_initial`. | Resuelto |
| P-09 | 20/10/2026 | El laboratorio puede no tener internet el día de la defensa. | Bootstrap, iconos y Chart.js se sirven localmente (`static/vendor`). El simulador ESP32 y el broker corren en Docker local. | Resuelto |
| P-10 | 20/10/2026 | El modelo de simulación en Arena comprometido en la Entrega 1 no está terminado. | Se usará la exportación `ordenes.csv` (tiempos reales) para ajustar las distribuciones del modelo. | **Abierto**: planificado para la defensa |
| P-11 | 20/10/2026 | No hay sensores físicos ni PLC en la planta (declarado en la Entrega 1). | Los niveles 0-1 se emulan (simulador Python / Wokwi) con la misma interfaz MQTT que usaría el hardware real. | Limitación declarada |
