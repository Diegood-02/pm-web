"""Fixtures de integración contra PostgreSQL.

Las pruebas SIEMPRE usan TEST_DATABASE_URL (o la base pm_web_test por defecto),
nunca la DATABASE_URL del entorno. Además se exige que el nombre de la base
contenga "test" para no borrar una base de desarrollo por accidente.
"""

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://pm:cambia-esta-clave@localhost:5432/pm_web_test",
)
os.environ["JWT_SECRET_KEY"] = "clave-de-prueba-solo-para-tests-0123456789"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173"

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.security import hash_password  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
PASSWORD = "contraseña-segura-123"
API = "/api/v1"

Headers = dict[str, str]


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    if "test" not in (engine.url.database or ""):
        raise RuntimeError("Las pruebas solo corren contra una base cuyo nombre contiene 'test'")
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    yield
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user() -> Callable[..., int]:
    """Crea un usuario directamente en la base y devuelve su id."""

    def _make(email: str, role: Role = Role.MEMBER, *, active: bool = True) -> int:
        with SessionLocal() as session:
            user = User(
                email=email,
                full_name=email.split("@")[0],
                password_hash=hash_password(PASSWORD),
                role=role,
                is_active=active,
            )
            session.add(user)
            session.commit()
            return user.id

    return _make


@pytest.fixture
def login(client: TestClient) -> Callable[[str], Headers]:
    def _login(email: str) -> Headers:
        response = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


@pytest.fixture
def pm_headers(make_user: Callable[..., int], login: Callable[[str], Headers]) -> Headers:
    make_user("pm@ejemplo.com", Role.PROJECT_MANAGER)
    return login("pm@ejemplo.com")


@pytest.fixture
def create_project(client: TestClient) -> Callable[..., dict[str, Any]]:
    """Crea un proyecto con calendario de lunes a viernes, empezando el lunes 5 de enero de 2026."""

    def _create(headers: Headers, **overrides: Any) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": "Proyecto de prueba",
            "start_date": "2026-01-05",
            "working_weekdays": [0, 1, 2, 3, 4],
            "hours_per_day": 8,
        }
        body.update(overrides)
        response = client.post(f"{API}/projects", json=body, headers=headers)
        assert response.status_code == 201, response.text
        return dict(response.json())

    return _create


@pytest.fixture
def create_task(client: TestClient) -> Callable[..., dict[str, Any]]:
    def _create(headers: Headers, project_id: int, **body: Any) -> dict[str, Any]:
        response = client.post(f"{API}/projects/{project_id}/tasks", json=body, headers=headers)
        assert response.status_code == 201, response.text
        return dict(response.json())

    return _create
