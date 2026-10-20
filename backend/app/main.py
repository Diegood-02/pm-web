"""Punto de entrada de la API FastAPI (prefijo /api/v1)."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.routers import audit as audit_router
from app.routers import (
    auth,
    baselines,
    costs,
    dependencies,
    projects,
    resources,
    schedule,
    tasks,
    users,
)
from app.scheduling import SchedulingError

API_PREFIX = "/api/v1"

app = FastAPI(title="PM Web API", version="0.2.0", openapi_url=f"{API_PREFIX}/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(SchedulingError)
async def _scheduling_error(_: Request, exc: SchedulingError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(exc)}
    )


@app.exception_handler(IntegrityError)
async def _integrity_error(_: Request, __: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Conflicto con los datos existentes (duplicado o referencia inválida)"},
    )


@app.get(f"{API_PREFIX}/health", tags=["sistema"])
def health() -> dict[str, str]:
    """Indica que la API está en ejecución."""
    return {"status": "ok"}


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
    audit_router.router,
):
    app.include_router(router, prefix=API_PREFIX)
