"""Tareas del proyecto: CRUD, jerarquía WBS y reordenamiento."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.config import get_settings
from app.deps import CurrentUser, DbSession, ProjectReader, ProjectWriter, get_task_in_project
from app.models import Task
from app.schemas import TaskCreate, TaskMove, TaskOut, TaskUpdate
from app.services.audit import record
from app.services.scheduling import (
    children_index,
    descendant_ids,
    list_task_rows,
    task_wbs_codes,
)

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tareas"])

_CONFLICT = "La tarea fue modificada por otra persona. Recarga antes de guardar."


def _task_out(task: Task, wbs: str) -> TaskOut:
    return TaskOut(
        id=task.id,
        parent_id=task.parent_id,
        wbs=wbs,
        position=task.position,
        name=task.name,
        duration_days=task.duration_days,
        is_milestone=task.is_milestone,
        fixed_cost=task.fixed_cost,
        actual_cost=task.actual_cost,
        percent_complete=task.percent_complete,
        version=task.version,
    )


def _check_version(task: Task, version: int) -> None:
    if task.version != version:
        raise HTTPException(status.HTTP_409_CONFLICT, _CONFLICT)


def _require_parent(db: DbSession, project_id: int, parent_id: int | None) -> None:
    if parent_id is None:
        return
    parent = db.get(Task, parent_id)
    if parent is None or parent.project_id != project_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "El padre no existe en este proyecto"
        )


@router.get("", response_model=list[TaskOut])
def list_tasks(project: ProjectReader, db: DbSession) -> list[TaskOut]:
    rows = list_task_rows(db, project.id)
    codes = task_wbs_codes(rows)
    ordered = sorted(rows, key=lambda row: codes[row.id])
    return [_task_out(row, codes[row.id]) for row in ordered]


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    body: TaskCreate, project: ProjectWriter, user: CurrentUser, db: DbSession
) -> TaskOut:
    _require_parent(db, project.id, body.parent_id)
    cap = get_settings().max_tasks_per_project
    total = (
        db.scalar(select(func.count()).select_from(Task).where(Task.project_id == project.id)) or 0
    )
    if total >= cap:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"El proyecto alcanzó el límite de {cap} tareas",
        )
    next_position = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.project_id == project.id, Task.parent_id == body.parent_id)
        )
        or 0
    )
    task = Task(
        project_id=project.id,
        parent_id=body.parent_id,
        position=next_position,
        name=body.name,
        duration_days=0 if body.is_milestone else body.duration_days,
        is_milestone=body.is_milestone,
        fixed_cost=body.fixed_cost,
    )
    db.add(task)
    db.flush()
    record(
        db,
        user=user,
        project_id=project.id,
        action="create",
        entity="task",
        entity_id=task.id,
        changes={"name": task.name, "parent_id": task.parent_id},
    )
    db.commit()
    db.refresh(task)
    return _task_out(task, task_wbs_codes(list_task_rows(db, project.id))[task.id])


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, body: TaskUpdate, project: ProjectWriter, user: CurrentUser, db: DbSession
) -> TaskOut:
    task = get_task_in_project(db, project, task_id)
    _check_version(task, body.version)

    is_milestone = task.is_milestone if body.is_milestone is None else body.is_milestone
    duration = task.duration_days if body.duration_days is None else body.duration_days
    if is_milestone and duration != 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Un hito debe tener duración 0")

    changes: dict[str, Any] = {}
    for field, value in (
        ("name", body.name),
        ("duration_days", body.duration_days),
        ("is_milestone", body.is_milestone),
        ("fixed_cost", body.fixed_cost),
        ("actual_cost", body.actual_cost),
        ("percent_complete", body.percent_complete),
    ):
        if value is not None and getattr(task, field) != value:
            changes[field] = value
            setattr(task, field, value)
    if task.is_milestone:
        task.duration_days = 0
    if changes:
        task.version += 1
        record(
            db,
            user=user,
            project_id=project.id,
            action="update",
            entity="task",
            entity_id=task.id,
            changes=changes,
        )
    db.commit()
    db.refresh(task)
    return _task_out(task, task_wbs_codes(list_task_rows(db, project.id))[task.id])


@router.post("/{task_id}/move", response_model=TaskOut)
def move_task(
    task_id: int, body: TaskMove, project: ProjectWriter, user: CurrentUser, db: DbSession
) -> TaskOut:
    """Mueve la tarea a otro padre y/o posición entre sus hermanas (reordenar)."""
    task = get_task_in_project(db, project, task_id)
    _check_version(task, body.version)
    rows = list_task_rows(db, project.id)
    if body.parent_id is not None:
        _require_parent(db, project.id, body.parent_id)
        if body.parent_id == task.id or body.parent_id in descendant_ids(rows, task.id):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "No puedes mover una tarea dentro de sí misma o de sus subtareas",
            )

    children = children_index(rows)
    old_parent_id = task.parent_id
    siblings = [row for row in children.get(body.parent_id, []) if row.id != task.id]
    siblings.insert(min(body.position, len(siblings)), task)
    task.parent_id = body.parent_id
    for index, sibling in enumerate(siblings):
        sibling.position = index
    if old_parent_id != body.parent_id:
        remaining = [row for row in children.get(old_parent_id, []) if row.id != task.id]
        for index, sibling in enumerate(remaining):
            sibling.position = index

    task.version += 1
    record(
        db,
        user=user,
        project_id=project.id,
        action="move",
        entity="task",
        entity_id=task.id,
        changes={"parent_id": body.parent_id, "position": body.position},
    )
    db.commit()
    db.refresh(task)
    return _task_out(task, task_wbs_codes(list_task_rows(db, project.id))[task.id])


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, project: ProjectWriter, user: CurrentUser, db: DbSession) -> None:
    """Borra la tarea con sus subtareas, dependencias y asignaciones (cascada en la base)."""
    task = get_task_in_project(db, project, task_id)
    record(
        db,
        user=user,
        project_id=project.id,
        action="delete",
        entity="task",
        entity_id=task.id,
        changes={"name": task.name},
    )
    db.delete(task)
    db.commit()
