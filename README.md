# ERP Blancos Aromáticos

Sistema ERP + MES básico + IIoT para **Productos Químicos de Limpieza Blancos Aromáticos** (Tipitapa, Nicaragua).
Proyecto Integrador de *Sistemas de Manufactura (SX002)*, UNI, 2026. Equipo 5T1-SIS.

| Integrante | Rol en el proyecto | Usuario del sistema | Rol en el sistema |
|---|---|---|---|
| Bricio Osmundo José Morales López | Líder de proyecto | `bmorales` | Gerencia, Administrador |
| Dylan Gustavo Davila Torres | Desarrollador / configurador ERP-MES | `ddavila` | Administrador (superusuario) |
| Owen Espinoza | Analista de procesos | `oespinoza` | Compras, Almacén |
| Kevin Antonio Peryman | Responsable de integración IIoT | `kperyman` | Producción |
| Ashly Daniela Salazar Estrada | Responsable de documentación | `asalazar` | Calidad |
| Amaru Zamora | Responsable de análisis de datos y KPI | `azamora` | Gerencia, Ventas |

Contraseña de demostración de todos los usuarios (incluido `admin`): **`Blancos2026!`**

---

## 1. Puesta en marcha (cualquier computadora con Docker Desktop)

```bash
docker compose up --build
```

Abrir **http://localhost:8000** e ingresar con un usuario de la tabla.

La primera vez el contenedor:
1. crea las tablas en PostgreSQL;
2. carga los datos maestros del caso (productos, BOM, rutas, proveedores, clientes, parámetros de calidad, sensores, usuarios);
3. genera **6 semanas de operación** ejecutando los mismos servicios que usa la interfaz (compras, recepciones, producción, inspecciones, no conformidades, ventas), para que los KPI salgan de transacciones reales.

Servicios que se levantan:

| Servicio | Puerto | Nivel ISA-95 | Qué hace |
|---|---|---|---|
| `web` | 8000 | 4 y 3 | ERP + MES (Django 5.2 + gunicorn) |
| `db` | 5433 | 4 | PostgreSQL 16 (expuesto para pandas / Power BI) |
| `mqtt` | 1883 | 2 | Broker Mosquitto |
| `puente-mqtt` | — | 2→3 | Adapter MQTT → API HTTP del ERP |
| `simulador-esp32` | — | 0-1 | Emula los ESP32 de planta (nivel, pH, temperatura, conteo) |

Comandos útiles:

```bash
docker compose down -v && docker compose up --build        # reiniciar con base limpia
docker compose exec web python iot/simulador_esp32.py --pico  # forzar una alarma IIoT en vivo (93 °C)
docker compose exec web python analisis/kpi_analisis.py       # análisis Pandas + carta SPC
docker compose exec web pytest -q                             # pruebas automáticas
docker compose logs -f puente-mqtt                            # ver el flujo de datos de planta
```

**Plan B sin Docker:** `pip install -r requirements.txt && python manage.py migrate && python manage.py cargar_datos_caso --historial && python manage.py runserver` (usa SQLite automáticamente si no hay `POSTGRES_HOST`).

## 2. Qué cubre (guía del Proyecto Integrador)

| Componente mínimo | Dónde verlo en el sistema |
|---|---|
| Datos maestros | Menú *Ingeniería y maestros* (productos, proveedores, clientes, almacenes, UdM, centros) |
| BOM y rutas | *BOM y rutas*: BOM de 2 niveles (desinfectante, piloto) y 3 niveles (línea ECO); explosión con costos |
| Flujo transaccional | Compras → Recepción (crea lotes) → Producción (consume por lote FEFO) → Inventario → Ventas/Despacho |
| MES básico | Órdenes de trabajo por operación con tiempos y paros, lote por orden, inspecciones, no conformidades y disposición |
| Integración adicional | IIoT (ESP32 → MQTT → ERP, lecturas ligadas a la orden y al lote) + análisis de datos en Pandas (SPC) |
| KPI | OEE (D×R×C), Yield, FPY, rotación de inventario, costo unitario real vs. estándar, tiempo de ciclo, litros de aceite reciclado |
| Trazabilidad | *Lotes y trazabilidad*: genealogía hacia atrás (hasta proveedor) y hacia adelante (hasta cliente) |

## 3. Arquitectura

```
Nivel 4 ERP   ┌─ maestros ─ ingenieria ─ compras ─ inventario ─ ventas ─ kpi ─┐   Django + PostgreSQL
Nivel 3 MES   │            produccion (órdenes, operaciones, consumos)        │   misma base, capa de servicios
              │            calidad (inspecciones, NC, disposición)            │
              └───────────────▲─────────────────────────────────────────────────┘
                              │ HTTP POST /iiot/api/lecturas/ (JSON + X-IIoT-Token)
Nivel 2       puente MQTT (Adapter)  ◄── broker Mosquitto ◄── tópicos blancosaromaticos/planta/#
Nivel 1-0     ESP32 (simulador Python o Wokwi): HC-SR04 nivel, pH, temperatura reactor, IR conteo
```

Patrones de diseño: capas + **Service Layer**, **Unit of Work** (`transaction.atomic`), **State** (estados de OC/OP/pedido/NC),
**Ledger** (movimientos de inventario inmutables), **Composite** (BOM multinivel), **Strategy** (disposición de NC),
**Observer** (alertas IIoT por señal), **Adapter** (puente MQTT).

```
apps/
  core/         auditoría, permisos por rol, tablero, comando cargar_datos_caso
  maestros/     productos, UdM, almacenes, proveedores, clientes, centros de trabajo
  ingenieria/   BOM (Composite) y rutas
  inventario/   lotes, libro mayor de movimientos, FEFO, trazabilidad, vista SQL v_existencias
  compras/      orden de compra y recepción
  produccion/   órdenes de producción, órdenes de trabajo, consumos, costeo
  calidad/      parámetros, inspecciones, no conformidades (Strategy)
  ventas/       pedidos y despachos
  iiot/         dispositivos, sensores, lecturas, alertas (Observer), API de ingesta
  kpi/          cálculo de indicadores, tablero, exportaciones CSV, API JSON
iot/            puente MQTT, simulador ESP32, sketch Wokwi
analisis/       análisis Pandas/Matplotlib (KPI independientes + carta de control SPC)
docs/           bitácora, cambios vs. Entrega 1, problemas, uso de IA, guion de demo, evidencias
tests/          pruebas del flujo completo (pytest)
```

## 4. Documentación del proyecto

- [docs/cambios_entrega1.md](docs/cambios_entrega1.md): cambios respecto al diseño de la Entrega 1 y su justificación
- [docs/problemas.md](docs/problemas.md): registro de problemas y su resolución
- [docs/bitacora.md](docs/bitacora.md): bitácora de aportes por integrante
- [docs/uso_ia.md](docs/uso_ia.md): declaración de uso de herramientas de IA (sección 11 de la guía)
- [docs/guion_demo.md](docs/guion_demo.md): guion de la demostración en vivo
- [docs/evidencias/](docs/evidencias/): capturas y salidas del análisis
