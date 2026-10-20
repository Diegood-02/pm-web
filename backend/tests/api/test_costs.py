"""Costos y valor ganado por API, con el escenario de referencia de tests/costing/test_evm.py.

- Tarea A: 5 días, Ana a 100/h al 100 %, costo fijo 500 -> presupuesto 4 500.
- Tarea B: 2 días, Beto a 50/h al 50 % -> presupuesto 400. Va después de A.
- Corte: miércoles 7 de enero de 2026. A al 50 %, costo real 2 400.
- PV = 2 700, EV = 2 250, AC = 2 400, CPI = 0.9375, SPI = 0.8333 (alerta de SPI).
"""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.models import Role
from tests.conftest import API, Headers


def _build_reference_project(
    client: TestClient,
    pm: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    project = create_project(pm)
    pid = project["id"]
    ana = client.post(
        f"{API}/projects/{pid}/resources",
        json={"name": "Ana", "hourly_rate": 100, "max_units": 100},
        headers=pm,
    ).json()
    beto = client.post(
        f"{API}/projects/{pid}/resources",
        json={"name": "Beto", "hourly_rate": 50, "max_units": 100},
        headers=pm,
    ).json()
    a = create_task(pm, pid, name="A", duration_days=5, fixed_cost=500)
    b = create_task(pm, pid, name="B", duration_days=2)
    client.post(
        f"{API}/projects/{pid}/dependencies",
        json={"predecessor_id": a["id"], "successor_id": b["id"]},
        headers=pm,
    )
    client.post(
        f"{API}/projects/{pid}/tasks/{a['id']}/assignments",
        json={"resource_id": ana["id"], "units_percent": 100},
        headers=pm,
    )
    client.post(
        f"{API}/projects/{pid}/tasks/{b['id']}/assignments",
        json={"resource_id": beto["id"], "units_percent": 50},
        headers=pm,
    )
    updated = client.patch(
        f"{API}/projects/{pid}/tasks/{a['id']}",
        json={"version": a["version"], "percent_complete": 50, "actual_cost": 2400},
        headers=pm,
    )
    assert updated.status_code == 200, updated.text
    return {"project_id": pid, "a": a, "b": b}


def test_reporte_de_costos_coincide_con_el_calculo_a_mano(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    ref = _build_reference_project(client, pm_headers, create_project, create_task)

    response = client.get(
        f"{API}/projects/{ref['project_id']}/costs",
        params={"status_date": "2026-01-07"},
        headers=pm_headers,
    )

    assert response.status_code == 200, response.text
    summary = response.json()["summary"]
    assert summary["bac"] == 4900
    assert summary["pv"] == 2700
    assert summary["ev"] == 2250
    assert summary["ac"] == 2400
    assert summary["cv"] == -150
    assert summary["sv"] == -450
    assert summary["cpi"] == 0.9375
    assert summary["spi"] == 0.8333
    assert summary["cpi_alert"] is False
    assert summary["spi_alert"] is True
    assert summary["threshold"] == 0.9


def test_detalle_por_tarea_muestra_presupuesto_y_valores(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    ref = _build_reference_project(client, pm_headers, create_project, create_task)

    body = client.get(
        f"{API}/projects/{ref['project_id']}/costs",
        params={"status_date": "2026-01-07"},
        headers=pm_headers,
    ).json()

    by_name = {row["name"]: row for row in body["tasks"]}
    assert by_name["A"]["budget"] == 4500
    assert by_name["A"]["planned_value"] == 2700
    assert by_name["A"]["earned_value"] == 2250
    assert by_name["B"]["budget"] == 400
    assert by_name["B"]["planned_value"] == 0


def test_alerta_de_cpi_cuando_el_costo_real_supera_el_presupuesto(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    ref = _build_reference_project(client, pm_headers, create_project, create_task)
    a = client.get(f"{API}/projects/{ref['project_id']}/tasks", headers=pm_headers).json()[0]
    client.patch(
        f"{API}/projects/{ref['project_id']}/tasks/{a['id']}",
        json={"version": a["version"], "actual_cost": 3000},
        headers=pm_headers,
    )

    summary = client.get(
        f"{API}/projects/{ref['project_id']}/costs",
        params={"status_date": "2026-01-07"},
        headers=pm_headers,
    ).json()["summary"]

    assert summary["cpi"] == 0.75
    assert summary["cpi_alert"] is True


def test_linea_base_guarda_el_presupuesto_de_cada_tarea(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    ref = _build_reference_project(client, pm_headers, create_project, create_task)
    baseline = client.post(
        f"{API}/projects/{ref['project_id']}/baselines", json={"name": "Plan"}, headers=pm_headers
    ).json()

    detail = client.get(
        f"{API}/projects/{ref['project_id']}/baselines/{baseline['id']}", headers=pm_headers
    ).json()

    budgets = {task["name"]: task["budget"] for task in detail["tasks"]}
    assert budgets == {"A": 4500, "B": 400}


def test_costos_invalidos_se_rechazan(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    pid = create_project(pm_headers)["id"]
    task = create_task(pm_headers, pid, name="X", duration_days=1)
    url = f"{API}/projects/{pid}/tasks/{task['id']}"

    too_much = client.patch(url, json={"version": 1, "percent_complete": 101}, headers=pm_headers)
    negative_rate = client.post(
        f"{API}/projects/{pid}/resources",
        json={"name": "Negativo", "hourly_rate": -5},
        headers=pm_headers,
    )

    assert too_much.status_code == 422
    assert negative_rate.status_code == 422


def test_lector_puede_leer_costos_pero_no_registrar_avance(
    client: TestClient,
    make_user: Callable[..., int],
    login: Callable[[str], Headers],
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    ref = _build_reference_project(client, pm_headers, create_project, create_task)
    lector_id = make_user("lector@ejemplo.com", Role.READER)
    client.post(
        f"{API}/projects/{ref['project_id']}/members",
        json={"user_id": lector_id, "role": "lector"},
        headers=pm_headers,
    )
    lector = login("lector@ejemplo.com")

    read = client.get(f"{API}/projects/{ref['project_id']}/costs", headers=lector)
    write = client.patch(
        f"{API}/projects/{ref['project_id']}/tasks/{ref['a']['id']}",
        json={"version": ref["a"]["version"], "percent_complete": 90},
        headers=lector,
    )

    assert read.status_code == 200
    assert write.status_code == 403
