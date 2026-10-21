"""Exportación e importación por API. Incluye el ciclo completo exportar -> importar."""

import csv
import io
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.exports.project_json import validate_document
from app.models import Role
from tests.conftest import API, Headers


def _reference_project(
    client: TestClient,
    pm: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> int:
    pid: int = create_project(pm, name="Migración ERP")["id"]
    ana = client.post(
        f"{API}/projects/{pid}/resources",
        json={"name": "Ana", "hourly_rate": 100},
        headers=pm,
    ).json()
    a = create_task(pm, pid, name="A", duration_days=5, fixed_cost=500)
    client.patch(
        f"{API}/projects/{pid}/tasks/{a['id']}",
        json={"version": a["version"], "percent_complete": 50, "actual_cost": 2400},
        headers=pm,
    )
    b = create_task(pm, pid, name="B", duration_days=2)
    fase = create_task(pm, pid, name="Fase 2")
    create_task(pm, pid, name="Hija", duration_days=1, parent_id=fase["id"])
    client.post(
        f"{API}/projects/{pid}/dependencies",
        json={"predecessor_id": a["id"], "successor_id": b["id"], "type": "FS", "lag_days": 1},
        headers=pm,
    )
    client.post(
        f"{API}/projects/{pid}/tasks/{a['id']}/assignments",
        json={"resource_id": ana["id"], "units_percent": 100},
        headers=pm,
    )
    return pid


def test_descargas_de_cronograma_y_resumen(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    pid = _reference_project(client, pm_headers, create_project, create_task)

    csv_response = client.get(f"{API}/projects/{pid}/export/schedule.csv", headers=pm_headers)
    xlsx_response = client.get(f"{API}/projects/{pid}/export/schedule.xlsx", headers=pm_headers)
    pdf_response = client.get(
        f"{API}/projects/{pid}/export/summary.pdf",
        params={"status_date": "2026-01-07"},
        headers=pm_headers,
    )

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "attachment" in csv_response.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(csv_response.content.decode("utf-8-sig"))))
    assert [row[1] for row in rows[1:]] == ["A", "B", "Fase 2", "Hija"]
    assert rows[1][2] == "No"

    assert xlsx_response.status_code == 200
    workbook = load_workbook(io.BytesIO(xlsx_response.content))
    assert workbook["Cronograma"]["B2"].value == "A"

    assert pdf_response.status_code == 200
    assert pdf_response.content.startswith(b"%PDF-")


def test_exportacion_json_es_valida_y_se_puede_reimportar(
    client: TestClient,
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    pid = _reference_project(client, pm_headers, create_project, create_task)
    original_schedule = client.get(f"{API}/projects/{pid}/schedule", headers=pm_headers).json()
    document = client.get(f"{API}/projects/{pid}/export/project.json", headers=pm_headers).json()
    assert validate_document(document) == []

    document["project"]["name"] = "Copia de Migración"
    imported = client.post(f"{API}/projects/import", json=document, headers=pm_headers)

    assert imported.status_code == 201, imported.text
    new_id = imported.json()["id"]
    assert new_id != pid
    copy_schedule = client.get(f"{API}/projects/{new_id}/schedule", headers=pm_headers).json()
    assert copy_schedule["duration_days"] == original_schedule["duration_days"]
    assert copy_schedule["project_finish"] == original_schedule["project_finish"]
    original_names = {t["name"]: t["start_date"] for t in original_schedule["tasks"]}
    copy_names = {t["name"]: t["start_date"] for t in copy_schedule["tasks"]}
    assert copy_names == original_names
    assert [t["wbs"] for t in copy_schedule["tasks"]] == [
        t["wbs"] for t in original_schedule["tasks"]
    ]

    copy_costs = client.get(
        f"{API}/projects/{new_id}/costs", params={"status_date": "2026-01-07"}, headers=pm_headers
    ).json()
    # A: 100/h * 8 h * 5 días + 500 de costo fijo = 4 500; B no tiene asignaciones.
    assert copy_costs["summary"]["bac"] == 4500
    assert copy_costs["summary"]["ac"] == 2400

    resources = client.get(f"{API}/projects/{new_id}/resources", headers=pm_headers).json()
    assert [(r["name"], r["hourly_rate"]) for r in resources] == [("Ana", 100)]


def test_importar_documento_invalido_responde_422_con_errores(
    client: TestClient, pm_headers: Headers
) -> None:
    response = client.post(
        f"{API}/projects/import",
        json={
            "format": "otro",
            "schema_version": 1,
            "project": {},
            "resources": [],
            "tasks": [],
            "dependencies": [],
            "assignments": [],
        },
        headers=pm_headers,
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert response.json()["detail"]


def test_solo_pm_o_admin_importan_y_un_miembro_no(
    client: TestClient,
    make_user: Callable[..., int],
    login: Callable[[str], Headers],
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    pid = _reference_project(client, pm_headers, create_project, create_task)
    document = client.get(f"{API}/projects/{pid}/export/project.json", headers=pm_headers).json()
    make_user("miembro@ejemplo.com", Role.MEMBER)

    response = client.post(
        f"{API}/projects/import", json=document, headers=login("miembro@ejemplo.com")
    )

    assert response.status_code == 403


def test_lector_puede_descargar_y_externo_no(
    client: TestClient,
    make_user: Callable[..., int],
    login: Callable[[str], Headers],
    pm_headers: Headers,
    create_project: Callable[..., dict[str, Any]],
    create_task: Callable[..., dict[str, Any]],
) -> None:
    pid = _reference_project(client, pm_headers, create_project, create_task)
    make_user("externo@ejemplo.com", Role.MEMBER)
    lector_id = make_user("lector2@ejemplo.com", Role.READER)
    client.post(
        f"{API}/projects/{pid}/members",
        json={"user_id": lector_id, "role": "lector"},
        headers=pm_headers,
    )

    reader = client.get(
        f"{API}/projects/{pid}/export/schedule.csv", headers=login("lector2@ejemplo.com")
    )
    outsider = client.get(
        f"{API}/projects/{pid}/export/schedule.csv", headers=login("externo@ejemplo.com")
    )

    assert reader.status_code == 200
    assert outsider.status_code == 404
