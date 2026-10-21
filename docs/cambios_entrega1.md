# Cambios respecto al diseño de la Entrega 1

La guía exige "declarar y justificar los cambios respecto al diseño original" (ítem 12). Se listan todos.

| # | Diseño Entrega 1 | Implementación Entrega 2 | Justificación |
|---|---|---|---|
| 1 | ERP sobre **Odoo 17 Community** | **Desarrollo propio**: Django 5.2 + PostgreSQL 16, en Docker | El módulo *Quality* de Odoo es solo Enterprise (de pago), y la guía exige no conformidades con disposición. El desarrollo propio, aceptado por la guía (§3.2), permite explicar cada tabla y cada flujo de datos en la defensa ("dónde nace y dónde muere cada dato"). Se mantiene PostgreSQL, la misma base de Odoo. |
| 2 | MES con *Work Orders* de Odoo | Módulo `produccion`: órdenes de trabajo por operación con inicio, fin, operador y paros | Mismo concepto funcional. Los tiempos reales y los paros alimentan el OEE. |
| 3 | HMI nivel 2 en **Streamlit** | Panel de monitoreo IIoT dentro del ERP (Chart.js, refresco cada 3 s) | Una sola aplicación y menos piezas que fallen en la demo en vivo. Lee las mismas lecturas que llegan por MQTT. |
| 4 | BOM nivel 2 "según formulación validada" | Cantidades de prueba: agua 96,5 L + amonio cuaternario 2,0 L + solubilizante 1,5 L por 100 L de base | La Entrega 1 dejó las cantidades como supuesto por validar. Se usan cantidades de prueba, editables y versionables (BOM v1.0). |
| 5 | Ruta OP-10 a OP-40 en un solo producto | OP-10 y OP-20 en la orden de la **base desinfectante** (semielaborado); OP-30 y OP-40 en la orden del **producto terminado**. Mismos códigos y tiempos (30/60/30/60 min) | Con una BOM de dos niveles, el semielaborado se fabrica con su propia orden y lote, lo que da trazabilidad del lote de base. |
| 6 | Componentes nivel 1: base, fragancia, colorante, envase | Se agregan **etiqueta con código de lote** y **caja de 4 unidades** | Atiende los puntos de dolor del AS-IS: "etiquetado manual sin código de lote" y "embalaje en cajas de 4 unidades". |
| 7 | Un producto piloto | Se agrega una **segunda línea: Jabón líquido multiusos ECO 1 L con aceite de cocina reciclado** (BOM de 3 niveles) | Ampliación de alcance alineada con el enfoque de sostenibilidad del equipo. El piloto (desinfectante) se mantiene sin cambios. |
| 8 | Controles pH / viscosidad / apariencia | Parámetros con límites: desinfectante pH 6,5–7,5 (de la Entrega 1), viscosidad 10–50 cP y densidad 0,990–1,030 g/mL; aceite usado: acidez ≤ 4 mg KOH/g y humedad ≤ 2 % | Los límites hacen la inspección verificable. Los valores distintos al pH se declaran como supuestos técnicos. |
| 9 | Sensores: HC-SR04 (nivel) e IR (conteo) | Se agregan **pH en tanque** y **temperatura del reactor** | Variables críticas de la saponificación (línea ECO). Permiten demostrar alertas de proceso ligadas a una no conformidad. |
| 10 | Simulación en **Arena 14.7** | **Pendiente** (no se entrega en la Entrega 2) | La integración exigida se cubre con IIoT y análisis de datos. El modelo de Arena se planifica para la defensa final y usará los tiempos reales registrados (exportación CSV de órdenes). |
| 11 | Roles: Dylan analista, Owen configurador; Amaru sin rol | Dylan desarrollador/configurador ERP-MES, Owen analista de procesos, Amaru análisis de datos y KPI | Redistribución acordada por el equipo según la carga de la implementación. |
