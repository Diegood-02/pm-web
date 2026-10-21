from fastapi.testclient import TestClient

from tests.conftest import API

ENDPOINTS_FASE_2 = [
    f"{API}/auth/login",
    f"{API}/auth/refresh",
    f"{API}/auth/me",
    f"{API}/users",
    f"{API}/projects",
    f"{API}/projects/{{project_id}}/members",
    f"{API}/projects/{{project_id}}/tasks",
    f"{API}/projects/{{project_id}}/tasks/{{task_id}}/move",
    f"{API}/projects/{{project_id}}/dependencies",
    f"{API}/projects/{{project_id}}/resources",
    f"{API}/projects/{{project_id}}/tasks/{{task_id}}/assignments",
    f"{API}/projects/{{project_id}}/baselines",
    f"{API}/projects/{{project_id}}/baselines/{{baseline_id}}/comparison",
    f"{API}/projects/{{project_id}}/schedule",
    f"{API}/projects/{{project_id}}/audit",
]


def test_openapi_documenta_todos_los_endpoints_de_la_fase_2(client: TestClient) -> None:
    response = client.get(f"{API}/openapi.json")

    assert response.status_code == 200
    documented = response.json()["paths"]
    missing = [path for path in ENDPOINTS_FASE_2 if path not in documented]
    assert missing == []
