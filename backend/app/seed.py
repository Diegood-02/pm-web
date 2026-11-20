"""Proyecto de ejemplo de 40 tareas para demos y pruebas manuales del piloto.

El proyecto se construye como documento del formato JSON v1, se valida y se importa
con el mismo código que usa la importación de la API. Así el ejemplo también prueba
esa ruta cada vez que se genera.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.exports.project_json import build_document, validate_document
from app.models import Project, User
from app.services.exports import import_document

HOURS_PER_DAY = 8.0
OVERRUN = (
    1.05  # El costo real de las tareas en curso supera al presupuesto un 5 %: ejemplo de alerta.
)

# Cada fase: nombre y ocho tareas (nombre, duración en días, recurso, unidades %).
PHASES: list[tuple[str, list[tuple[str, int, str, int]]]] = [
    (
        "Inicio",
        [
            ("Acta de constitución", 2, "Ana", 100),
            ("Identificación de interesados", 1, "Ana", 50),
            ("Plan de comunicación", 2, "Ana", 50),
            ("Análisis de alcance inicial", 3, "Beto", 100),
            ("Estimación de presupuesto", 2, "Ana", 50),
            ("Selección de proveedor", 3, "Beto", 50),
            ("Contrato firmado", 1, "Ana", 100),
            ("Kickoff con el cliente", 1, "Ana", 100),
        ],
    ),
    (
        "Análisis",
        [
            ("Levantamiento de requerimientos", 5, "Beto", 100),
            ("Entrevistas con áreas", 4, "Beto", 100),
            ("Mapeo de procesos actuales", 4, "Beto", 100),
            ("Diseño de arquitectura", 4, "Carla", 100),
            ("Modelo de datos", 3, "Carla", 100),
            ("Plan de pruebas", 2, "Dani", 100),
            ("Validación de requerimientos", 2, "Beto", 50),
            ("Aprobación de diseño con el cliente", 2, "Ana", 50),
        ],
    ),
    (
        "Construcción",
        [
            ("Configuración de módulo financiero", 8, "Carla", 100),
            ("Configuración de inventarios", 8, "Carla", 100),
            ("Configuración de compras", 6, "Carla", 100),
            ("Integración con CRM", 7, "Carla", 100),
            ("Migración de catálogos", 5, "Carla", 50),
            ("Migración de saldos", 4, "Carla", 100),
            ("Desarrollo de reportes", 6, "Carla", 100),
            ("Pruebas unitarias", 4, "Dani", 100),
        ],
    ),
    (
        "Despliegue",
        [
            ("Pruebas de aceptación de usuario", 5, "Dani", 100),
            ("Capacitación a usuarios", 6, "Eva", 100),
            ("Manual de operación", 3, "Eva", 50),
            ("Plan de contingencia", 2, "Ana", 50),
            ("Puesta en producción", 2, "Carla", 100),
            ("Soporte post arranque", 10, "Dani", 50),
            ("Cierre técnico", 1, "Carla", 50),
            ("Cierre administrativo", 1, "Ana", 50),
        ],
    ),
]

RESOURCES: dict[str, int] = {"Ana": 850, "Beto": 420, "Carla": 510, "Dani": 380, "Eva": 350}

# Avance de ejemplo: fase 1 terminada, fase 2 terminada salvo la última tarea, fase 3 en curso.
PERCENT_BY_INDEX: dict[str, list[int]] = {
    "Inicio": [100] * 8,
    "Análisis": [100] * 7 + [40],
    "Construcción": [100] * 5 + [30, 0, 0],
    "Despliegue": [0] * 8,
}


def demo_document() -> dict[str, Any]:
    resources: list[dict[str, Any]] = [
        {"id": index, "name": name, "max_units": 100, "hourly_rate": rate}
        for index, (name, rate) in enumerate(RESOURCES.items(), start=1)
    ]
    resource_id = {str(res["name"]): int(res["id"]) for res in resources}

    tasks: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    next_id = 1
    previous_milestone: int | None = None

    for phase_name, items in PHASES:
        phase_id = next_id
        tasks.append(_task(phase_id, None, phase_name, 0, False, 0.0, 0.0, 0))
        next_id += 1
        percents = PERCENT_BY_INDEX[phase_name]
        phase_task_ids: list[int] = []
        for index, (name, duration, resource, units) in enumerate(items):
            task_id = next_id
            next_id += 1
            budget = RESOURCES[resource] * units / 100 * HOURS_PER_DAY * duration
            percent = percents[index]
            actual = round(budget * percent / 100 * OVERRUN, 2)
            tasks.append(_task(task_id, phase_id, name, duration, False, 0.0, actual, percent))
            assignments.append(
                {"task_id": task_id, "resource_id": resource_id[resource], "units_percent": units}
            )
            phase_task_ids.append(task_id)

        milestone_id = next_id
        next_id += 1
        milestone_percent = 100 if all(value == 100 for value in percents) else 0
        tasks.append(
            _task(
                milestone_id,
                phase_id,
                f"Hito: fin de {phase_name}",
                0,
                True,
                0.0,
                0.0,
                milestone_percent,
            )
        )

        # Cadena de la fase: cada tarea sigue a la anterior; el hito cierra la fase.
        chain = phase_task_ids + [milestone_id]
        for pred, succ in zip(chain, chain[1:], strict=False):
            dependencies.append(
                {"predecessor_id": pred, "successor_id": succ, "type": "FS", "lag_days": 0}
            )
        if previous_milestone is not None:
            dependencies.append(
                {
                    "predecessor_id": previous_milestone,
                    "successor_id": phase_task_ids[0],
                    "type": "FS",
                    "lag_days": 0,
                }
            )
        previous_milestone = milestone_id

    # Relaciones de otros tipos, siempre hacia adelante en el orden: no crean ciclos.
    construction = [
        t["id"]
        for t in tasks
        if t["parent_id"] is not None and _phase_of(tasks, t) == "Construcción"
    ]
    dependencies.append(
        {
            "predecessor_id": construction[3],
            "successor_id": construction[4],
            "type": "SS",
            "lag_days": 2,
        }
    )
    dependencies.append(
        {
            "predecessor_id": construction[6],
            "successor_id": construction[7],
            "type": "FF",
            "lag_days": 0,
        }
    )

    return build_document(
        project={
            "name": "Proyecto demo: implantación de ERP",
            "description": "Proyecto de ejemplo con 40 tareas para demos y pruebas del piloto.",
            "timezone": "America/Mexico_City",
            "start_date": "2026-03-02",
            "working_weekdays": [0, 1, 2, 3, 4],
            "hours_per_day": HOURS_PER_DAY,
            "holidays": ["2026-04-02", "2026-04-03"],
            "extra_working_days": [],
        },
        tasks=tasks,
        resources_list=resources,
        dependencies=dependencies,
        assignments=assignments,
    )


def _task(
    task_id: int,
    parent_id: int | None,
    name: str,
    duration: int,
    is_milestone: bool,
    fixed_cost: float,
    actual_cost: float,
    percent: int,
) -> dict[str, Any]:
    return {
        "id": task_id,
        "parent_id": parent_id,
        "name": name,
        "duration_days": duration,
        "is_milestone": is_milestone,
        "fixed_cost": fixed_cost,
        "actual_cost": actual_cost,
        "percent_complete": percent,
    }


def _phase_of(tasks: list[dict[str, Any]], task: dict[str, Any]) -> str:
    parent = next(t for t in tasks if t["id"] == task["parent_id"])
    return str(parent["name"])


def seed_demo_project(db: Session, owner: User) -> Project:
    """Crea el proyecto de ejemplo. Lanza ValueError si el documento generado no es válido."""
    document = demo_document()
    errors = validate_document(document)
    if errors:
        raise ValueError("El proyecto de ejemplo no es válido: " + "; ".join(errors))
    return import_document(db, owner, document)
