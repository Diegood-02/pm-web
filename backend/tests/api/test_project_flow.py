"""Flujo completo por API (entregable de la Fase 2):

crear proyecto -> tareas -> dependencias -> ruta crítica -> línea base -> comparación.
"""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import API, Headers


def _tasks_by_name(client: TestClient, pm: Headers, project_id: int) -> dict[str, dict[str, Any]]:
    tasks = client.get(f"{API}/projects/{project_id}/tasks", headers=pm).json()
    return {task["name"]: task for task in tasks}


def test_flujo_completo_con_ruta_critica(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project = create_project(pm_headers)
    project_id = project["id"]
    a = create_task(pm_headers, project_id, name="A", duration_days=3)
    b = create_task(pm_headers, project_id, name="B", duration_days=2)
    c = create_task(pm_headers, project_id, name="C", duration_days=4)
    for pred, succ in ((a, b), (b, c)):
        response = client.post(
            f"{API}/projects/{project_id}/dependencies",
            json={"predecessor_id": pred["id"], "successor_id": succ["id"], "type": "FS"},
            headers=pm_headers,
        )
        assert response.status_code == 201, response.text

    schedule = client.get(f"{API}/projects/{project_id}/schedule", headers=pm_headers)

    assert schedule.status_code == 200
    body = schedule.json()
    assert body["duration_days"] == 9
    assert body["project_finish"] == "2026-01-15"
    assert body["critical_path"] == [a["id"], b["id"], c["id"]]
    by_id = {task["task_id"]: task for task in body["tasks"]}
    assert by_id[b["id"]]["start_date"] == "2026-01-08"
    assert by_id[c["id"]]["finish_date"] == "2026-01-15"
    assert all(by_id[t["id"]]["is_critical"] for t in (a, b, c))


def test_ciclo_en_dependencias_se_rechaza(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    a = create_task(pm_headers, project_id, name="A", duration_days=1)
    b = create_task(pm_headers, project_id, name="B", duration_days=1)
    client.post(
        f"{API}/projects/{project_id}/dependencies",
        json={"predecessor_id": a["id"], "successor_id": b["id"]},
        headers=pm_headers,
    )

    response = client.post(
        f"{API}/projects/{project_id}/dependencies",
        json={"predecessor_id": b["id"], "successor_id": a["id"]},
        headers=pm_headers,
    )

    assert response.status_code == 422
    assert "Ciclo" in response.json()["detail"]
    assert (
        len(client.get(f"{API}/projects/{project_id}/dependencies", headers=pm_headers).json()) == 1
    )


def test_dependencia_duplicada_y_autodependencia(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project_id = create_project(pm_headers)["id"]
    a = create_task(pm_headers, project_id, name="A", duration_days=1)
    b = create_task(pm_headers, project_id, name="B", duration_days=1)
    url = f"{API}/projects/{project_id}/dependencies"
    body = {"predecessor_id": a["id"], "successor_id": b["id"], "type": "SS"}

    assert client.post(url, json=body, headers=pm_headers).status_code == 201
    assert client.post(url, json=body, headers=pm_headers).status_code == 409
    self_dep = {"predecessor_id": a["id"], "successor_id": a["id"]}
    assert client.post(url, json=self_dep, headers=pm_headers).status_code == 422


def test_dependencia_hacia_tarea_de_otro_proyecto_responde_404(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    first = create_project(pm_headers)["id"]
    second = create_project(pm_headers, name="Otro")["id"]
    a = create_task(pm_headers, first, name="A")
    b = create_task(pm_headers, second, name="B")

    response = client.post(
        f"{API}/projects/{first}/dependencies",
        json={"predecessor_id": a["id"], "successor_id": b["id"]},
        headers=pm_headers,
    )

    assert response.status_code == 404


def test_calendario_con_feriado_mueve_la_ruta(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    project = create_project(pm_headers, holidays=["2026-01-06"])
    create_task(pm_headers, project["id"], name="A", duration_days=3)

    body = client.get(f"{API}/projects/{project['id']}/schedule", headers=pm_headers).json()

    # Lunes 5, miércoles 7 y jueves 8: el feriado del martes 6 se salta.
    assert body["project_finish"] == "2026-01-08"


def test_pm_ve_y_actualiza_el_proyecto_y_los_cambios_se_auditan(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
) -> None:
    project = create_project(pm_headers)

    updated = client.patch(
        f"{API}/projects/{project['id']}",
        json={"version": project["version"], "name": "Renombrado", "timezone": "Europe/Madrid"},
        headers=pm_headers,
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Renombrado"
    assert updated.json()["version"] == project["version"] + 1
    audit = client.get(f"{API}/projects/{project['id']}/audit", headers=pm_headers).json()
    assert any(entry["action"] == "update" and entry["entity"] == "project" for entry in audit)
