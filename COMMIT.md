# Commit de Amaru Zamora (Análisis de datos y KPI)

Orden de turno: espera a que el integrante anterior haya hecho push (ver INSTRUCCIONES.md).

## Qué agregas
- apps/kpi y templates/kpi: cálculo de KPI, tablero, exportaciones CSV y API JSON.
- analisis/kpi_analisis.py y docs/evidencias/analisis: validación cruzada en Pandas y carta SPC.

## Pasos
```bash
git clone https://github.com/OwenEspinoza11/Manufactura.git     # solo la primera vez
cd Manufactura
git pull
git config user.name  "TU NOMBRE"                     # tu identidad, no la de otro
git config user.email "tu-correo-de-github@ejemplo.com"
```
Copia el CONTENIDO de esta carpeta (menos este COMMIT.md) dentro de la carpeta Manufactura, respetando las rutas.
Abre docs/bitacora.md y completa tu fila (fecha, actividad, evidencia, estado).

```bash
git add -A
git commit -m "feat(kpi): tablero de indicadores (OEE, yield, FPY, rotación, costo) y análisis Pandas/SPC"
git push
```
