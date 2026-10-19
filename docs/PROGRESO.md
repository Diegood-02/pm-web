# Progreso del proyecto

Última actualización: 2026-10-19

| Fase | Descripción | Estado |
|------|-------------|--------|
| 0 | Repositorio y estructura | En revisión (pendiente: repo remoto, rama y primer commit) |
| 1 | Motor de programación (CPM) | Pendiente |
| 2 | Backend: modelo de datos y API | Pendiente |
| 3 | Frontend MVP | Pendiente |
| 4 | Costos y valor ganado (EVM) | Pendiente |
| 5 | Reportes y exportación | Pendiente |
| 6 | Piloto y endurecimiento | Pendiente |

## Fase 0. Detalle

- [x] Carpeta `pm-web/` creada en `Mis_progra`.
- [x] Repositorio git local inicializado (rama `main`, sin commits, sin remoto).
- [x] Estructura de `backend/`, `frontend/`, `docs/`.
- [x] `docker-compose.yml` con servicios `db`, `api` y `web`.
- [x] Dependencias del frontend instaladas con versiones exactas.
- [x] Linters y formateadores verificados (ruff, mypy, eslint, prettier).
- [x] Pruebas base en verde (pytest 1/1, Vitest 1/1).
- [x] `docker compose up` verificado: `db` healthy, `api` en :8000 (`/api/v1/health` responde ok), `web` en :5173 (HTTP 200).
- [x] Repositorio remoto público creado en `Diegood-02/pm-web` (solo creado; aún sin push).
- [ ] Primer push de `main` (pendiente de confirmación del commit).
- [ ] Rama `feature/mvp-pm-web` creada desde `main` (requiere primer commit, pendiente de confirmación).
- [ ] Primer commit propuesto y aprobado.
