"""WBS, reordenamiento, control de versiones, línea base, recursos y auditoría."""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import API, Headers


def _wbs(client: TestClient, pm: Headers, project_id: int) -> dict[str, str]:
    tasks = client.get(f"{API}/projects/{project_id}/tasks", headers=pm).json()
    return {task["name"]: task["wbs"] for task in tasks}


def test_wbs_refleja_la_jerarquia(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    fase = create_task(pm_headers, project_id, name="Fase 1")
    create_task(pm_headers, project_id, name="Diseño", parent_id=fase["id"])
    create_task(pm_headers, project_id, name="Pruebas", parent_id=fase["id"])
    create_task(pm_headers, project_id, name="Fase 2")

    assert _wbs(client, pm_headers, project_id) == {
        "Fase 1": "1",
        "Diseño": "1.1",
        "Pruebas": "1.2",
        "Fase 2": "2",
    }


def test_mover_tarea_reordena_hermanas_y_cambia_de_padre(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    fase = create_task(pm_headers, project_id, name="Fase")
    create_task(pm_headers, project_id, name="Diseño", parent_id=fase["id"])
    nueva = create_task(pm_headers, project_id, name="Nueva")

    moved = client.post(
        f"{API}/projects/{project_id}/tasks/{nueva['id']}/move",
        json={"version": nueva["version"], "parent_id": fase["id"], "position": 0},
        headers=pm_headers,
    )

    assert moved.status_code == 200
    assert _wbs(client, pm_headers, project_id) == {"Fase": "1", "Nueva": "1.1", "Diseño": "1.2"}


def test_no_se_puede_mover_una_tarea_dentro_de_sus_subtareas(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    padre = create_task(pm_headers, project_id, name="Padre")
    hija = create_task(pm_headers, project_id, name="Hija", parent_id=padre["id"])

    response = client.post(
        f"{API}/projects/{project_id}/tasks/{padre['id']}/move",
        json={"version": padre["version"], "parent_id": hija["id"], "position": 0},
        headers=pm_headers,
    )

    assert response.status_code == 422


def test_edicion_con_version_vieja_responde_409(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    task = create_task(pm_headers, project_id, name="Tarea", duration_days=2)
    url = f"{API}/projects/{project_id}/tasks/{task['id']}"

    first = client.patch(url, json={"version": 1, "duration_days": 5}, headers=pm_headers)
    assert first.status_code == 200
    assert first.json()["version"] == 2

    stale = client.patch(url, json={"version": 1, "duration_days": 9}, headers=pm_headers)
    assert stale.status_code == 409


def test_hito_no_puede_tener_duracion(
    client: TestClient, pm_headers: Headers, create_project: Callable[..., dict[str, Any]]
) -> None:
    project_id = create_project(pm_headers)["id"]

    response = client.post(
        f"{API}/projects/{project_id}/tasks",
        json={"name": "Hito", "is_milestone": True, "duration_days": 2},
        headers=pm_headers,
    )

    assert response.status_code == 422


def test_borrar_padre_borra_sus_subtareas(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    padre = create_task(pm_headers, project_id, name="Padre")
    create_task(pm_headers, project_id, name="Hija", parent_id=padre["id"])

    deleted = client.delete(f"{API}/projects/{project_id}/tasks/{padre['id']}", headers=pm_headers)

    assert deleted.status_code == 204
    assert client.get(f"{API}/projects/{project_id}/tasks", headers=pm_headers).json() == []


def test_linea_base_registra_y_compara_variaciones(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    a = create_task(pm_headers, project_id, name="A", duration_days=3)
    b = create_task(pm_headers, project_id, name="B", duration_days=2)
    c = create_task(pm_headers, project_id, name="C", duration_days=4)
    for pred, succ in ((a, b), (b, c)):
        client.post(
            f"{API}/projects/{project_id}/dependencies",
            json={"predecessor_id": pred["id"], "successor_id": succ["id"]},
            headers=pm_headers,
        )

    baseline = client.post(
        f"{API}/projects/{project_id}/baselines", json={"name": "Plan v1"}, headers=pm_headers
    )
    assert baseline.status_code == 201
    assert baseline.json()["project_finish"] == "2026-01-15"

    # Alargar B en 3 días desplaza a C y el fin del proyecto.
    client.patch(
        f"{API}/projects/{project_id}/tasks/{b['id']}",
        json={"version": b["version"], "duration_days": 5},
        headers=pm_headers,
    )
    comparison = client.get(
        f"{API}/projects/{project_id}/baselines/{baseline.json()['id']}/comparison",
        headers=pm_headers,
    ).json()

    by_name = {row["name"]: row for row in comparison}
    assert by_name["A"]["finish_variance_days"] == 0
    assert by_name["B"]["start_variance_days"] == 0
    assert by_name["B"]["finish_variance_days"] == 3
    assert by_name["C"]["start_variance_days"] == 3
    assert by_name["C"]["finish_variance_days"] == 3


def test_miembro_no_puede_crear_linea_base(
    client: TestClient,
    make_user: Callable[..., int],
    login: Callable[[str], Headers],
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    member_id = make_user("miembro@ejemplo.com")
    client.post(
        f"{API}/projects/{project_id}/members",
        json={"user_id": member_id, "role": "miembro"},
        headers=pm_headers,
    )

    response = client.post(
        f"{API}/projects/{project_id}/baselines",
        json={"name": "Intento"},
        headers=login("miembro@ejemplo.com"),
    )

    assert response.status_code == 403


def test_recursos_y_asignaciones(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    task = create_task(pm_headers, project_id, name="Codificar", duration_days=3)
    resource = client.post(
        f"{API}/projects/{project_id}/resources",
        json={"name": "Ana", "max_units": 100},
        headers=pm_headers,
    ).json()
    url = f"{API}/projects/{project_id}/tasks/{task['id']}/assignments"

    assigned = client.post(
        url, json={"resource_id": resource["id"], "units_percent": 50}, headers=pm_headers
    )
    assert assigned.status_code == 201
    repeated = client.post(
        url, json={"resource_id": resource["id"], "units_percent": 25}, headers=pm_headers
    )
    assert repeated.status_code == 409
    invalid_units = client.post(
        url, json={"resource_id": resource["id"], "units_percent": 0}, headers=pm_headers
    )
    assert invalid_units.status_code == 422

    listed = client.get(f"{API}/projects/{project_id}/assignments", headers=pm_headers).json()
    assert [(a["task_id"], a["units_percent"]) for a in listed] == [(task["id"], 50)]


def test_auditoria_registra_quien_cambio_que(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    create_task(pm_headers, project_id, name="Auditada", duration_days=1)

    entries = client.get(f"{API}/projects/{project_id}/audit", headers=pm_headers).json()

    creates = {(e["entity"], e["action"]) for e in entries}
    assert ("project", "create") in creates
    assert ("task", "create") in creates
    assert all(e["user_id"] is not None for e in entries)
