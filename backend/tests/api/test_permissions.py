"""Permisos por proyecto: un lector no edita, un no miembro no ve nada."""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.models import Role
from tests.conftest import API, Headers


def _add_member(client: TestClient, pm: Headers, project_id: int, user_id: int, role: str) -> None:
    response = client.post(
        f"{API}/projects/{project_id}/members",
        json={"user_id": user_id, "role": role},
        headers=pm,
    )
    assert response.status_code == 201, response.text


def test_no_miembro_no_ve_el_proyecto_ni_sus_recursos(
    client: TestClient,
    make_user: Callable[..., int],
    login: Callable[[str], Headers],
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project = create_project(pm_headers)
    create_task(pm_headers, project["id"], name="Secreta", duration_days=2)
    make_user("externo@ejemplo.com")
    external = login("externo@ejemplo.com")

    assert client.get(f"{API}/projects", headers=external).json() == []
    assert client.get(f"{API}/projects/{project['id']}", headers=external).status_code == 404
    assert client.get(f"{API}/projects/{project['id']}/tasks", headers=external).status_code == 404
    assert (
        client.get(f"{API}/projects/{project['id']}/schedule", headers=external).status_code == 404
    )


def test_lector_puede_leer_pero_no_editar(
    client: TestClient,
    make_user: Callable[..., int],
    login: Callable[[str], Headers],
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project = create_project(pm_headers)
    task = create_task(pm_headers, project["id"], name="Diseño", duration_days=3)
    lector_id = make_user("lector@ejemplo.com", Role.READER)
    _add_member(client, pm_headers, project["id"], lector_id, "lector")
    lector = login("lector@ejemplo.com")

    assert client.get(f"{API}/projects/{project['id']}/tasks", headers=lector).status_code == 200
    created = client.post(
        f"{API}/projects/{project['id']}/tasks", json={"name": "Nueva"}, headers=lector
    )
    assert created.status_code == 403
    renamed = client.patch(
        f"{API}/projects/{project['id']}/tasks/{task['id']}",
        json={"name": "Hack", "version": task["version"]},
        headers=lector,
    )
    assert renamed.status_code == 403


def test_miembro_edita_tareas_pero_no_administra_el_equipo(
    client: TestClient,
    make_user: Callable[..., int],
    login: Callable[[str], Headers],
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
) -> None:
    project = create_project(pm_headers)
    member_id = make_user("miembro@ejemplo.com", Role.MEMBER)
    _add_member(client, pm_headers, project["id"], member_id, "miembro")
    member = login("miembro@ejemplo.com")
    other_id = make_user("otro@ejemplo.com", Role.MEMBER)

    created = client.post(
        f"{API}/projects/{project['id']}/tasks", json={"name": "Tarea"}, headers=member
    )
    assert created.status_code == 201
    invite = client.post(
        f"{API}/projects/{project['id']}/members",
        json={"user_id": other_id, "role": "lector"},
        headers=member,
    )
    assert invite.status_code == 403
    baseline = client.post(
        f"{API}/projects/{project['id']}/baselines", json={"name": "BL"}, headers=member
    )
    assert baseline.status_code == 403


def test_solo_un_pm_o_admin_crea_proyectos(
    client: TestClient,
    make_user: Callable[..., int],
    login: Callable[[str], Headers],
) -> None:
    make_user("miembro@ejemplo.com", Role.MEMBER)
    body = {"name": "Nuevo", "start_date": "2026-01-05"}

    response = client.post(f"{API}/projects", json=body, headers=login("miembro@ejemplo.com"))

    assert response.status_code == 403


def test_el_creador_queda_como_project_manager(
    client: TestClient, pm_headers: Headers, create_project: Callable[..., dict[str, Any]]
) -> None:
    project = create_project(pm_headers)

    members = client.get(f"{API}/projects/{project['id']}/members", headers=pm_headers).json()

    assert [(m["email"], m["role"]) for m in members] == [("pm@ejemplo.com", "project_manager")]


def test_no_se_puede_quitar_al_ultimo_project_manager(
    client: TestClient, pm_headers: Headers, create_project: Callable[..., dict[str, Any]]
) -> None:
    project = create_project(pm_headers)
    pm_id = client.get(f"{API}/projects/{project['id']}/members", headers=pm_headers).json()[0][
        "user_id"
    ]

    response = client.delete(f"{API}/projects/{project['id']}/members/{pm_id}", headers=pm_headers)

    assert response.status_code == 422


def test_admin_global_accede_a_cualquier_proyecto(
    client: TestClient,
    make_user: Callable[..., int],
    login: Callable[[str], Headers],
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
) -> None:
    project = create_project(pm_headers)
    make_user("admin@ejemplo.com", Role.ADMIN)

    response = client.get(f"{API}/projects/{project['id']}", headers=login("admin@ejemplo.com"))

    assert response.status_code == 200


def test_cambio_de_proyecto_con_version_vieja_responde_409(
    client: TestClient, pm_headers: Headers, create_project: Callable[..., dict[str, Any]]
) -> None:
    project = create_project(pm_headers)
    first = client.patch(
        f"{API}/projects/{project['id']}", json={"version": 1, "name": "A"}, headers=pm_headers
    )
    assert first.status_code == 200

    stale = client.patch(
        f"{API}/projects/{project['id']}", json={"version": 1, "name": "B"}, headers=pm_headers
    )

    assert stale.status_code == 409
