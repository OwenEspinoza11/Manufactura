# Commit de Ashly Salazar (Responsable de documentación)

Orden de turno: espera a que el integrante anterior haya hecho push (ver INSTRUCCIONES.md).

## Qué agregas
- apps/calidad y templates/calidad: parámetros, inspecciones, NC y disposición (patrón Strategy).
- docs/problemas.md y docs/evidencias/README.md.

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
git commit -m "feat(calidad): inspecciones, no conformidades y disposición (scrap/retrabajo/liberación); registro de problemas"
git push
```
