# Commit de Bricio Morales (Líder de proyecto)

Orden de turno: espera a que el integrante anterior haya hecho push (ver INSTRUCCIONES.md).

## Qué agregas
- apps/ventas y templates/ventas: pedidos, confirmación y despacho por lote (solo lotes liberados).
- docs/guion_demo.md: guion de la demostración.
- docs/entrega1/: PDF de la Entrega 1.

## Pasos
```bash
git clone https://github.com/BobDylan8597/ERP.git     # solo la primera vez
cd ERP
git pull
git config user.name  "TU NOMBRE"                     # tu identidad, no la de otro
git config user.email "tu-correo-de-github@ejemplo.com"
```
Copia el CONTENIDO de esta carpeta (menos este COMMIT.md) dentro de la carpeta ERP, respetando las rutas.
Abre docs/bitacora.md y completa tu fila (fecha, actividad, evidencia, estado).

```bash
git add -A
git commit -m "feat(ventas): pedidos de venta y despacho FEFO por lote; guion de demo y Entrega 1"
git push
```
