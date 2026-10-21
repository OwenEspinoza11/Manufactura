# Declaración de uso de herramientas de inteligencia artificial

Conforme a la sección 11 de la guía del Proyecto Integrador.

| Herramienta | Uso | Partes del entregable |
|---|---|---|
| Claude Code (Anthropic), asistente de programación | Propuesta de arquitectura y patrones de diseño, generación y depuración de código, datos de prueba, pruebas automáticas y borradores de documentación técnica | Código en `apps/`, `iot/`, `analisis/`, `tests/`; archivos de `docs/` |

Compromisos del equipo:

- Cada integrante revisa el código y la documentación de su área y debe poder explicar cualquier línea o párrafo en la defensa.
- Las decisiones de diseño (plataforma, alcance, segunda línea ECO, roles) fueron tomadas por el equipo.
- Los datos del caso (empresa, producto piloto, ruta, tiempos estándar, límites de pH) provienen de la Entrega 1 del equipo. Los supuestos adicionales están declarados en `cambios_entrega1.md`.
- Bibliotecas de terceros usadas (con licencia libre): Django, psycopg, gunicorn, WhiteNoise, paho-mqtt, requests, pandas, Matplotlib, Bootstrap, Bootstrap Icons, Chart.js, PubSubClient (Arduino).
