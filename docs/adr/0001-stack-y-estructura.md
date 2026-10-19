# ADR 0001: Stack y estructura del repositorio

- Estado: aceptado
- Fecha: 2026-10-19

## Contexto

Se construye una aplicación web multiusuario de gestión de proyectos para un equipo, enfocada en el rol de Project Manager y en buenas prácticas del PMBOK, inspirada en ProjectLibre.

## Decisión

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, PostgreSQL 16. Pruebas con pytest. Calidad con ruff y mypy (modo estricto).
- **Frontend:** React 18 + TypeScript + Vite. Pruebas con Vitest y Testing Library. Calidad con ESLint y Prettier. Gantt con frappe-gantt (Fase 3).
- **Contenedores:** Docker Compose con los servicios `db`, `api` y `web`.
- **Estructura:** monorepo con `backend/`, `frontend/` y `docs/` en la raíz.
- **Dependencias fijadas:** frontend con versiones exactas (`--save-exact`); backend con rangos mínimos en `pyproject.toml`.

## Consecuencias

- Un solo repositorio simplifica versiones y revisiones, pero obliga a mantener ambos lados alineados en la misma rama.
- El motor de programación (Fase 1) vivirá en `backend/app/scheduling/` como funciones puras, sin dependencias de FastAPI ni de la base de datos.
