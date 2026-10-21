"""Puente entre los modelos de base de datos y el motor de programación.

Aquí se traduce el proyecto a objetos de dominio, se calcula el WBS y se
ejecuta el CPM. El motor en sí no conoce la base de datos.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Dependency as DependencyRow
from app.models import Project
from app.models import Task as TaskRow
from app.scheduling import Calendar, Dependency, Schedule, Task, compute_schedule


@dataclass(frozen=True, slots=True)
class TaskNode:
    """Tarea con su código WBS calculado."""

    row: TaskRow
    wbs: str


def project_calendar(project: Project) -> Calendar:
    return Calendar(
        working_weekdays=frozenset(project.working_weekdays),
        hours_per_day=project.hours_per_day,
        holidays=frozenset(date.fromisoformat(d) for d in project.holidays),
        extra_working_days=frozenset(date.fromisoformat(d) for d in project.extra_working_days),
    )


def list_task_rows(db: Session, project_id: int) -> list[TaskRow]:
    return list(
        db.scalars(
            select(TaskRow)
            .where(TaskRow.project_id == project_id)
            .order_by(TaskRow.position, TaskRow.id)
        )
    )


def children_index(rows: list[TaskRow]) -> dict[int | None, list[TaskRow]]:
    children: dict[int | None, list[TaskRow]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: (r.position, r.id)):
        children[row.parent_id].append(row)
    return children


def ordered_tasks(rows: list[TaskRow]) -> list[TaskNode]:
    """Recorre el árbol en orden WBS (profundidad primero) y asigna códigos 1, 1.1, 1.2, ..."""
    children = children_index(rows)
    result: list[TaskNode] = []

    def visit(parent_id: int | None, prefix: str) -> None:
        for index, row in enumerate(children.get(parent_id, []), start=1):
            code = f"{prefix}{index}"
            result.append(TaskNode(row=row, wbs=code))
            visit(row.id, f"{code}.")

    visit(None, "")
    return result


def domain_dependencies(db: Session, project_id: int) -> list[Dependency]:
    rows = db.scalars(select(DependencyRow).where(DependencyRow.project_id == project_id))
    return [
        Dependency(
            predecessor_id=row.predecessor_id,
            successor_id=row.successor_id,
            type=row.type,
            lag_days=row.lag_days,
        )
        for row in rows
    ]


def load_schedule(db: Session, project: Project) -> Schedule:
    rows = list_task_rows(db, project.id)
    domain_tasks = [
        Task(
            id=node.row.id,
            name=node.row.name,
            duration_days=node.row.duration_days,
            wbs=node.wbs,
            is_milestone=node.row.is_milestone,
        )
        for node in ordered_tasks(rows)
    ]
    return compute_schedule(
        domain_tasks,
        domain_dependencies(db, project.id),
        project_calendar(project),
        project.start_date,
    )


def task_wbs_codes(rows: list[TaskRow]) -> dict[int, str]:
    return {node.row.id: node.wbs for node in ordered_tasks(rows)}


def descendant_ids(rows: list[TaskRow], task_id: int) -> set[int]:
    children = children_index(rows)
    found: set[int] = set()
    stack = [task_id]
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child.id not in found:
                found.add(child.id)
                stack.append(child.id)
    return found
