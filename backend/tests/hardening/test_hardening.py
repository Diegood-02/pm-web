"""Pruebas de endurecimiento: cabeceras, límites, errores, login, logs y datos de ejemplo."""

import json
import logging
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.exports.project_json import validate_document
from app.logging_config import JsonFormatter
from app.main import app
from app.models import Role, Task, User
from app.ratelimit import login_limiter
from app.seed import demo_document, seed_demo_project
from app.services.scheduling import load_schedule
from tests.conftest import API, PASSWORD, Headers


@app.get(f"{API}/_prueba/error")
def _provoca_error() -> None:
    raise RuntimeError("detalle interno que no debe salir")


@pytest.fixture(autouse=True)
def _limpia_limitador() -> None:
    login_limiter.reset()


def test_respuesta_incluye_id_de_peticion_y_cabeceras_de_seguridad(client: TestClient) -> None:
    response = client.get(f"{API}/health")

    assert response.status_code == 200
    assert len(response.headers["x-request-id"]) >= 16
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_id_de_peticion_recibido_se_devuelve_tal_cual(client: TestClient) -> None:
    response = client.get(f"{API}/health", headers={"X-Request-ID": "pilot-123"})

    assert response.headers["x-request-id"] == "pilot-123"


def test_respuestas_de_autenticacion_no_se_cachean(client: TestClient) -> None:
    response = client.post(f"{API}/auth/login", json={"email": "x@ejemplo.com", "password": "x"})

    assert response.headers["cache-control"] == "no-store"


def test_cuerpo_demasiado_grande_responde_413(client: TestClient) -> None:
    too_big = b"{" + b"a" * (get_settings().max_request_bytes + 10)

    response = client.post(
        f"{API}/auth/login", content=too_big, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 413
    assert response.json()["detail"].startswith("El cuerpo")


def test_error_no_controlado_responde_500_sin_detalles_internos() -> None:
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.get(f"{API}/_prueba/error")

    assert response.status_code == 500
    assert response.json()["detail"] == "Error interno del servidor"
    assert "detalle interno" not in response.text
    assert response.json()["request_id"]


def test_health_ready_comprueba_la_base(client: TestClient) -> None:
    response = client.get(f"{API}/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_login_se_bloquea_tras_intentos_fallidos(
    client: TestClient, make_user: Callable[..., int]
) -> None:
    make_user("ana@ejemplo.com")
    wrong = {"email": "ana@ejemplo.com", "password": "clave-incorrecta-123"}
    for _ in range(get_settings().login_max_failures):
        assert client.post(f"{API}/auth/login", json=wrong).status_code == 401

    blocked = client.post(
        f"{API}/auth/login", json={"email": "ana@ejemplo.com", "password": PASSWORD}
    )

    assert blocked.status_code == 429


def test_login_exitoso_limpia_los_fallos_previos(
    client: TestClient, make_user: Callable[..., int]
) -> None:
    make_user("ana@ejemplo.com")
    wrong = {"email": "ana@ejemplo.com", "password": "clave-incorrecta-123"}
    for _ in range(get_settings().login_max_failures - 1):
        client.post(f"{API}/auth/login", json=wrong)
    assert (
        client.post(
            f"{API}/auth/login", json={"email": "ana@ejemplo.com", "password": PASSWORD}
        ).status_code
        == 200
    )

    for _ in range(get_settings().login_max_failures - 1):
        client.post(f"{API}/auth/login", json=wrong)

    assert (
        client.post(
            f"{API}/auth/login", json={"email": "ana@ejemplo.com", "password": PASSWORD}
        ).status_code
        == 200
    )


def test_limite_de_tareas_por_proyecto(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "max_tasks_per_project", 2)
    pid = create_project(pm_headers)["id"]
    create_task(pm_headers, pid, name="Uno")
    create_task(pm_headers, pid, name="Dos")

    response = client.post(f"{API}/projects/{pid}/tasks", json={"name": "Tres"}, headers=pm_headers)

    assert response.status_code == 422
    assert "límite de 2 tareas" in response.json()["detail"]


def test_formato_de_log_es_json_con_id_de_peticion() -> None:
    record = logging.LogRecord("app.access", logging.INFO, __file__, 1, "request", None, None)
    record.fields = {"method": "GET", "status": 200}

    line = JsonFormatter().format(record)
    parsed = json.loads(line)

    assert parsed["message"] == "request"
    assert parsed["status"] == 200
    assert parsed["level"] == "INFO"
    assert "request_id" in parsed


def test_proyecto_de_ejemplo_tiene_40_tareas_y_ruta_critica(make_user: Callable[..., int]) -> None:
    assert validate_document(demo_document()) == []
    owner_id = make_user("pm-demo@ejemplo.com", Role.PROJECT_MANAGER)

    with SessionLocal() as session:
        owner = session.get(User, owner_id)
        assert owner is not None
        project = seed_demo_project(session, owner)
        task_count = session.scalar(
            select(func.count()).select_from(Task).where(Task.project_id == project.id)
        )
        schedule = load_schedule(session, project)

    assert task_count == 40
    assert schedule.duration_days > 0
    assert len(schedule.critical_path) > 0
