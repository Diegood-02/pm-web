# Progreso del proyecto

Última actualización: 2026-10-19

| Fase | Descripción | Estado |
|------|-------------|--------|
| 0 | Repositorio y estructura | Aprobada y publicada |
| 1 | Motor de programación (CPM) | En revisión (código y pruebas listos; pendiente de commit) |
| 2 | Backend: modelo de datos y API | Pendiente |
| 3 | Frontend MVP | Pendiente |
| 4 | Costos y valor ganado (EVM) | Pendiente |
| 5 | Reportes y exportación | Pendiente |
| 6 | Piloto y endurecimiento | Pendiente |

## Fase 0. Detalle

- [x] Carpeta `pm-web/` creada en `Mis_progra`.
- [x] Repositorio git inicializado; commit inicial `92d8156` en `main` publicado en `origin`.
- [x] Rama `feature/mvp-pm-web` creada desde `main` y publicada.
- [x] Estructura de `backend/`, `frontend/`, `docs/`.
- [x] `docker-compose.yml` con servicios `db`, `api` y `web`.
- [x] Dependencias del frontend instaladas con versiones exactas.
- [x] Linters y formateadores verificados (ruff, mypy, eslint, prettier).
- [x] Pruebas base en verde (pytest 1/1, Vitest 1/1).
- [x] `docker compose up` verificado: `db` healthy, `api` en :8000 (`/api/v1/health` responde ok), `web` en :5173 (HTTP 200).
- [x] Repositorio remoto público: https://github.com/Diegood-02/pm-web

## Fase 1. Detalle

- [x] Modelos de dominio: `Task`, `Dependency` (FS/SS/FF/SF, retraso negativo) y `Calendar` (días laborables, feriados, excepciones).
- [x] CPM: pase hacia adelante y hacia atrás, holguras total y libre, ruta crítica y detección de ciclos con error claro.
- [x] Calendario respetado al sumar duraciones (fines de semana, feriados y días excepcionales).
- [x] Pruebas: cadena lineal, paralelismo, los cuatro tipos de dependencia, retrasos negativos, hitos, calendario, ciclo y validaciones (28 pruebas en verde).
- [x] `ruff`, `ruff format`, `mypy` (estricto) sin errores.
- [x] Supuestos documentados en `docs/scheduling.md`.
- [ ] Commits propuestos y aprobados.
