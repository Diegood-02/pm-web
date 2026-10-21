"""Punto de entrada de la API FastAPI (prefijo /api/v1)."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import get_settings
from app.db import engine
from app.logging_config import configure_logging
from app.middleware import (
    BodyLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    request_id_var,
)
from app.routers import audit as audit_router
from app.routers import (
    auth,
    baselines,
    costs,
    dependencies,
    exports,
    projects,
    resources,
    schedule,
    tasks,
    users,
)
from app.scheduling import SchedulingError

API_PREFIX = "/api/v1"
logger = logging.getLogger("app")

_settings = get_settings()
configure_logging(_settings.log_level)

app = FastAPI(title="PM Web API", version="0.3.0", openapi_url=f"{API_PREFIX}/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
# Se aplican de dentro hacia fuera: cabeceras de seguridad, límite de tamaño y, al final,
# el id de petición, para que también las respuestas 413 lo lleven.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodyLimitMiddleware, max_bytes=_settings.max_request_bytes)
app.add_middleware(RequestContextMiddleware)


def _error(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "request_id": request_id_var.get()},
    )


@app.exception_handler(SchedulingError)
async def _scheduling_error(_: Request, exc: SchedulingError) -> JSONResponse:
    return _error(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))


@app.exception_handler(IntegrityError)
async def _integrity_error(_: Request, __: IntegrityError) -> JSONResponse:
    return _error(
        status.HTTP_409_CONFLICT,
        "Conflicto con los datos existentes (duplicado o referencia inválida)",
    )


@app.exception_handler(Exception)
async def _unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    # Nunca se devuelve el mensaje de la excepción al cliente: puede revelar detalles internos.
    logger.error("error no controlado", exc_info=exc)
    return _error(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno del servidor")


@app.get(f"{API_PREFIX}/health", tags=["sistema"])
def health() -> dict[str, str]:
    """Indica que el proceso de la API está en ejecución."""
    return {"status": "ok"}


@app.get(f"{API_PREFIX}/health/ready", tags=["sistema"])
def ready() -> JSONResponse:
    """Indica que la API puede atender peticiones: comprueba la conexión a la base de datos."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        logger.error("base de datos no disponible en health/ready")
        return JSONResponse(status_code=503, content={"status": "error", "database": "unavailable"})
    return JSONResponse(content={"status": "ready", "database": "ok"})


for router in (
    auth.router,
    users.router,
    projects.router,
    tasks.router,
    dependencies.router,
    resources.router,
    baselines.router,
    schedule.router,
    costs.router,
    exports.router,
    audit_router.router,
):
    app.include_router(router, prefix=API_PREFIX)
