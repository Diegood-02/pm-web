"""Genera src/demo/snapshot.json con respuestas reales de la API para la demo de GitHub Pages.

Uso (con la API local corriendo y el usuario de demo creado):

    DEMO_PASSWORD=... python frontend/scripts/generate-demo-snapshot.py

La demo es de solo lectura: el snapshot guarda lo que devuelve la API para cada ruta GET.
No se guardan tokens ni contraseñas en el archivo generado.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

API = os.environ.get("DEMO_API_URL", "http://localhost:8000/api/v1")
EMAIL = os.environ.get("DEMO_EMAIL", "demo.pm@ejemplo.com")
PASSWORD = os.environ.get("DEMO_PASSWORD")
STATUS_DATE = os.environ.get("DEMO_STATUS_DATE", "2026-11-19")
OUTPUT = Path(__file__).resolve().parents[1] / "src" / "demo" / "snapshot.json"


def call(method: str, path: str, token: str | None = None, body: dict | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        raise SystemExit(f"{method} {path} -> {error.code}: {error.read().decode(errors='replace')}")


def main() -> None:
    if not PASSWORD:
        sys.exit("Define DEMO_PASSWORD con la contraseña del usuario de demo.")

    token = call("POST", "/auth/login", body={"email": EMAIL, "password": PASSWORD})["access_token"]
    me = call("GET", "/auth/me", token)
    projects = call("GET", "/projects", token)
    demo_projects = [p for p in projects if p["name"].startswith("Proyecto demo")]
    if not demo_projects:
        sys.exit("No hay proyecto de demo. Corre: docker compose exec api python -m app.cli seed-demo --email " + EMAIL)

    snapshot: dict[str, object] = {"/auth/me": me, "/projects": projects}
    for project in demo_projects:
        pid = project["id"]
        base = f"/projects/{pid}"
        snapshot[base] = call("GET", base, token)
        for part in ("members", "tasks", "dependencies", "schedule", "resources", "assignments", "baselines"):
            snapshot[f"{base}/{part}"] = call("GET", f"{base}/{part}", token)
        snapshot[f"{base}/costs"] = call("GET", f"{base}/costs?status_date={STATUS_DATE}", token)
        for baseline in snapshot[f"{base}/baselines"]:
            bid = baseline["id"]
            snapshot[f"{base}/baselines/{bid}"] = call("GET", f"{base}/baselines/{bid}", token)
            snapshot[f"{base}/baselines/{bid}/comparison"] = call(
                "GET", f"{base}/baselines/{bid}/comparison", token
            )

    document = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status_date": STATUS_DATE,
        "note": "Datos de ejemplo generados desde la API. La demo es de solo lectura.",
        "responses": snapshot,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Snapshot escrito en {OUTPUT} con {len(snapshot)} respuestas.")


if __name__ == "__main__":
    main()
