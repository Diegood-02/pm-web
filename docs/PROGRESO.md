# Progreso del proyecto

Última actualización: 2026-10-19

| Fase | Descripción | Estado |
|------|-------------|--------|
| 0 | Repositorio y estructura | Aprobada y publicada |
| 1 | Motor de programación (CPM) | Aprobada y publicada |
| 2 | Backend: modelo de datos y API | Aprobada y publicada |
| 3 | Frontend MVP | En revisión (código y pruebas listos; pendiente de commit) |
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
- [x] Commits aprobados y publicados en `feature/mvp-pm-web`.

## Fase 2. Detalle

- [x] Modelos: User, Team, Project, ProjectMember, Task (jerarquía por `parent_id`), Dependency, Resource, Assignment (porcentaje), Baseline (+ BaselineTask), Comment, AuditLog.
- [x] Migración inicial con Alembic (`alembic/versions/`), aplicada en la base local de desarrollo.
- [x] Auth: login, refresh, perfil (`/api/v1/auth/*`). Alta de usuarios solo por admin. Primer admin con `python -m app.cli create-admin`.
- [x] Proyectos: CRUD, membresías con roles por proyecto, control de versión (409 ante edición concurrente).
- [x] Tareas: CRUD, mover y reordenar en el WBS, código WBS calculado.
- [x] Dependencias: crear y validar (sin ciclos, sin duplicados, sin autodependencias).
- [x] Recursos y asignaciones con porcentaje de dedicación.
- [x] Línea base: crear, consultar y comparar contra el plan actual (variaciones en días laborables).
- [x] Cronograma: endpoint que ejecuta el motor CPM y devuelve fechas, holguras y ruta crítica.
- [x] Auditoría: cada cambio se registra con usuario, acción y cambios; consulta para project managers.
- [x] Permisos: no miembro → 404; lector no edita (403); miembro no administra equipo ni línea base (403).
- [x] Pruebas de integración contra PostgreSQL real (`pm_web_test`): 61 en verde, incluido el flujo completo y OpenAPI.
- [x] `ruff`, `ruff format`, `mypy` (estricto) sin errores.
- [x] Prueba de humo en el contenedor `api`: login, perfil, proyecto, tarea y cronograma.
- [x] Decisiones en `docs/adr/0002-persistencia-y-autorizacion.md`.
- [x] Commits aprobados y publicados en `feature/mvp-pm-web`.
- [ ] Comentarios de tareas: modelo listo, sin endpoints (pendiente de decisión).

## Fase 3. Detalle

- [x] Login y sesión (`/login`), con renovación de token y cierre de sesión.
- [x] Lista de proyectos y creación de proyectos (PM y admin).
- [x] Gestión de usuarios para admin: alta, cambio de rol y activación.
- [x] Vista de proyecto con pestañas Tareas, Gantt, Recursos y Línea base (navegación con teclado).
- [x] Tareas: tabla con WBS editable, subir, bajar, sangría, eliminar y hitos.
- [x] Gantt con `frappe-gantt`: ruta crítica en rojo y tabla de dependencias con su tipo exacto.
- [x] Dependencias: crear y eliminar desde la pestaña Gantt.
- [x] Recursos y asignaciones con porcentaje de dedicación.
- [x] Línea base: guardar (PM) y comparar contra el plan actual.
- [x] Actualización: recarga cada 15 segundos y después de cada cambio propio.
- [x] Concurrencia: 409 muestra aviso y recarga; no sobrescribe en silencio.
- [x] Pruebas con Vitest: 27 en verde (cliente API, login, pestañas, tabla de tareas, Gantt, permisos y conflicto 409).
- [x] `tsc`, ESLint, Prettier y build de producción sin errores.
- [x] Decisiones en `docs/adr/0003-frontend-y-actualizacion.md`.
- [x] Docker Compose con el frontend verificado: `web` sirve la app (HTTP 200) con las dependencias nuevas.
- [ ] Vulnerabilidades de herramientas de desarrollo (`npm audit`): pendiente de decisión.
- [ ] Commits propuestos y aprobados.
