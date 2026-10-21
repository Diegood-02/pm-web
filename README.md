# PM Web

Aplicación web multiusuario de gestión de proyectos para equipos, enfocada en el rol de Project Manager y en buenas prácticas del PMBOK.

Estado: **Fase 0 (repositorio y estructura)**. Ver [docs/PROGRESO.md](docs/PROGRESO.md).

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, PostgreSQL 16
- Frontend: React, TypeScript, Vite
- Contenedores: Docker Compose

## Requisitos

- Docker Desktop con Docker Compose v2
- Python 3.12 y Node.js 24 (solo para correr pruebas y linters fuera de Docker)

## Puesta en marcha

```bash
cp .env.example .env   # ajusta las claves antes de usarlo fuera de local
docker compose up --build
```

- API: http://localhost:8000/api/v1/health
- Documentación OpenAPI: http://localhost:8000/docs
- Web: http://localhost:5173

## Comandos

| Comando | Qué hace |
|---------|----------|
| `make up` | Levanta los servicios con Docker Compose |
| `make down` | Detiene los servicios |
| `make test` | Corre pytest y Vitest |
| `make lint` | Corre ruff, mypy, ESLint y Prettier |
| `make migrate` | Migraciones de Alembic (Fase 2) |

## Documentación

- [Progreso](docs/PROGRESO.md)
- [ADR 0001: stack y estructura](docs/adr/0001-stack-y-estructura.md)
- [ADR 0002: persistencia, autenticación y autorización](docs/adr/0002-persistencia-y-autorizacion.md)

## Primer administrador

Después de `make migrate`, crea el primer usuario administrador. La contraseña se pide por consola:

```bash
docker compose exec -it api python -m app.cli create-admin --email tu@correo.com --name "Tu nombre"
```

Los demás usuarios los da de alta un admin desde `POST /api/v1/users`.

## API

- Documentación interactiva: http://localhost:8000/docs
- Especificación OpenAPI: http://localhost:8000/api/v1/openapi.json
- Todas las rutas empiezan con `/api/v1`. Las rutas protegidas requieren `Authorization: Bearer <access_token>`.

## Pruebas de integración

Las pruebas de la API usan PostgreSQL real. Crea una base de pruebas en el contenedor `db` (solo una vez):

```bash
docker compose exec -T db psql -U pm -d pm_web -c "CREATE DATABASE pm_web_test;"
cd backend && python -m pytest
```

Las pruebas nunca usan `DATABASE_URL`. Usan `TEST_DATABASE_URL` o `pm_web_test` por defecto, y se niegan a correr si el nombre de la base no contiene `test`.
