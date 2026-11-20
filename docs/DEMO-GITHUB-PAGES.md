# Demo en GitHub Pages

La demo es un sitio estático de **solo lectura** con datos de ejemplo. No hay backend ni base de datos en Pages: no se puede editar nada y no se expone ninguna API.

## Qué incluye

- Login de demostración: cualquier correo y contraseña entran como project manager.
- Lista de proyecto de ejemplo (40 tareas), cronograma, Gantt, recursos, costos (PV, EV, AC, CPI, SPI) y línea base con comparación.
- Las escrituras responden 403 con el aviso de solo lectura, y los botones de exportación no aparecen.

## Cómo funciona

- El frontend se compila con `VITE_DEMO=true`. En ese modo `frontend/src/demo/demoApi.ts` responde las llamadas a la API con `frontend/src/demo/snapshot.json`.
- `snapshot.json` se genera desde la API real con `frontend/scripts/generate-demo-snapshot.py`. No contiene tokens ni contraseñas.
- Las rutas usan `#/` (`VITE_ROUTER_MODE=hash`), porque Pages no reescribe las rutas de la aplicación.
- La ruta base es `/pm-web/` (`VITE_BASE_PATH`).
- El workflow `.github/workflows/pages.yml` corre las pruebas, compila la demo y la publica en cada cambio de `frontend/` en la rama `feature/mvp-pm-web`.

## Regenerar los datos de ejemplo

```bash
docker compose up -d db api
docker compose exec api python -m app.cli seed-demo --email demo.pm@ejemplo.com
DEMO_PASSWORD=<contraseña del usuario demo> python frontend/scripts/generate-demo-snapshot.py
```

Después confirma el cambio de `snapshot.json` y deja que el workflow publique la nueva versión.

## Límites

- La fecha de corte de costos es fija (`DEMO_STATUS_DATE` en el snapshot). Cambiarla en la pantalla no recalcula los valores.
- Las vistas que no estaban en el snapshot responden 404 con un aviso.
- No sustituye la instalación del piloto (ver `docs/RUNBOOK.md`).
