"""Formato propio de proyecto (JSON, versión 1): construcción y validación.

El documento usa referencias locales ("T1", "R1") en vez de ids de base de datos,
así que se puede importar en otra instancia. Las tareas se listan en orden WBS, y
el orden entre hermanas se conserva al importar.
"""

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from functools import lru_cache
from importlib import resources
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker

from app.scheduling import CyclicDependencyError, Dependency, DependencyType, check_acyclic

FORMAT_NAME = "pm-web-project"
SCHEMA_VERSION = 1


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    text = (
        resources.files("app.exports")
        .joinpath("project_v1.schema.json")
        .read_text(encoding="utf-8")
    )
    return Draft202012Validator(json.loads(text), format_checker=FormatChecker())


def build_document(
    project: Mapping[str, Any],
    tasks: Sequence[Mapping[str, Any]],
    resources_list: Sequence[Mapping[str, Any]],
    dependencies: Sequence[Mapping[str, Any]],
    assignments: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Arma el documento a partir de datos planos.

    tasks: en orden WBS, cada una con id, parent_id, name, duration_days, is_milestone,
           fixed_cost, actual_cost y percent_complete.
    dependencies: con predecessor_id, successor_id, type y lag_days.
    assignments: con task_id, resource_id y units_percent.
    """
    task_ref = {task["id"]: f"T{index}" for index, task in enumerate(tasks, start=1)}
    resource_ref = {res["id"]: f"R{index}" for index, res in enumerate(resources_list, start=1)}
    return {
        "format": FORMAT_NAME,
        "schema_version": SCHEMA_VERSION,
        "project": {
            "name": project["name"],
            "description": project.get("description", ""),
            "timezone": project["timezone"],
            "start_date": project["start_date"],
            "working_weekdays": sorted(project["working_weekdays"]),
            "hours_per_day": float(project["hours_per_day"]),
            "holidays": sorted(project.get("holidays", [])),
            "extra_working_days": sorted(project.get("extra_working_days", [])),
        },
        "resources": [
            {
                "ref": resource_ref[res["id"]],
                "name": res["name"],
                "max_units": res["max_units"],
                "hourly_rate": float(res["hourly_rate"]),
            }
            for res in resources_list
        ],
        "tasks": [
            {
                "ref": task_ref[task["id"]],
                "parent_ref": task_ref.get(task["parent_id"])
                if task["parent_id"] is not None
                else None,
                "name": task["name"],
                "duration_days": task["duration_days"],
                "is_milestone": task["is_milestone"],
                "fixed_cost": float(task["fixed_cost"]),
                "actual_cost": float(task["actual_cost"]),
                "percent_complete": task["percent_complete"],
            }
            for task in tasks
        ],
        "dependencies": [
            {
                "predecessor_ref": task_ref[dep["predecessor_id"]],
                "successor_ref": task_ref[dep["successor_id"]],
                "type": dep["type"],
                "lag_days": dep["lag_days"],
            }
            for dep in dependencies
        ],
        "assignments": [
            {
                "task_ref": task_ref[asg["task_id"]],
                "resource_ref": resource_ref[asg["resource_id"]],
                "units_percent": asg["units_percent"],
            }
            for asg in assignments
        ],
    }


def validate_document(raw: Any) -> list[str]:
    """Devuelve la lista de errores. Lista vacía significa que el documento es válido."""
    errors = [
        _format_error(error)
        for error in sorted(_validator().iter_errors(raw), key=lambda e: list(e.path))
    ]
    if errors or not isinstance(raw, dict):
        return errors
    return _semantic_errors(raw)


def _format_error(error: Any) -> str:
    location = "/".join(str(part) for part in error.path) or "documento"
    return f"{location}: {error.message}"


def _semantic_errors(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        ZoneInfo(doc["project"].get("timezone", "UTC"))
    except (ZoneInfoNotFoundError, ValueError):
        errors.append(f"project/timezone: zona horaria no válida: {doc['project']['timezone']}")

    for section, key in (("resources", "ref"), ("tasks", "ref")):
        errors.extend(_duplicates(doc[section], key, section))

    task_refs = {task["ref"]: index for index, task in enumerate(doc["tasks"])}
    resource_refs = {res["ref"] for res in doc["resources"]}

    for index, task in enumerate(doc["tasks"]):
        if task["is_milestone"] and task["duration_days"] != 0:
            errors.append(f"tasks/{index}: un hito debe tener duración 0")
        parent = task.get("parent_ref")
        if parent is not None and parent not in task_refs:
            errors.append(f"tasks/{index}: parent_ref desconocido: {parent}")
    errors.extend(_parent_cycle_errors(doc["tasks"]))

    dep_keys: Counter[tuple[str, str, DependencyType]] = Counter()
    domain_deps: list[Dependency] = []
    for index, dep in enumerate(doc["dependencies"]):
        pred, succ = dep["predecessor_ref"], dep["successor_ref"]
        if pred not in task_refs or succ not in task_refs:
            errors.append(f"dependencies/{index}: referencia a tarea desconocida")
            continue
        if pred == succ:
            errors.append(f"dependencies/{index}: una tarea no puede depender de sí misma")
            continue
        dep_type = DependencyType(dep.get("type", "FS"))
        dep_keys[(pred, succ, dep_type)] += 1
        domain_deps.append(
            Dependency(task_refs[pred], task_refs[succ], dep_type, dep.get("lag_days", 0))
        )
    for (pred, succ, dep_type), count in dep_keys.items():
        if count > 1:
            errors.append(f"dependencias repetidas: {pred} -> {succ} ({dep_type})")
    try:
        check_acyclic(range(len(doc["tasks"])), domain_deps)
    except CyclicDependencyError as exc:
        errors.append(str(exc))

    pairs: Counter[tuple[str, str]] = Counter()
    for index, asg in enumerate(doc["assignments"]):
        if asg["task_ref"] not in task_refs:
            errors.append(f"assignments/{index}: task_ref desconocido")
        if asg["resource_ref"] not in resource_refs:
            errors.append(f"assignments/{index}: resource_ref desconocido")
        pairs[(asg["task_ref"], asg["resource_ref"])] += 1
    for (task_ref, resource_ref), count in pairs.items():
        if count > 1:
            errors.append(f"asignación repetida: {task_ref} con {resource_ref}")
    return errors


def _duplicates(items: Sequence[Mapping[str, Any]], key: str, section: str) -> list[str]:
    counts = Counter(item[key] for item in items)
    return [f"{section}: ref repetida {ref}" for ref, count in counts.items() if count > 1]


def _parent_cycle_errors(tasks: Sequence[Mapping[str, Any]]) -> list[str]:
    parents = {task["ref"]: task.get("parent_ref") for task in tasks}
    errors: list[str] = []
    for ref in parents:
        seen = {ref}
        current = parents.get(ref)
        while current is not None and current in parents:
            if current in seen:
                errors.append(f"jerarquía circular en la tarea {ref}")
                break
            seen.add(current)
            current = parents[current]
    return errors
