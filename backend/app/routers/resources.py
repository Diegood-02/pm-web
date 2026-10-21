"""Recursos del proyecto y asignaciones a tareas (con porcentaje de dedicación)."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import CurrentUser, DbSession, ProjectReader, ProjectWriter, get_task_in_project
from app.models import Assignment, Resource
from app.schemas import (
    AssignmentCreate,
    AssignmentOut,
    ResourceCreate,
    ResourceOut,
    ResourceUpdate,
)
from app.services.audit import record

router = APIRouter(prefix="/projects/{project_id}", tags=["recursos"])


def _get_resource(db: DbSession, project_id: int, resource_id: int) -> Resource:
    resource = db.get(Resource, resource_id)
    if resource is None or resource.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso no encontrado")
    return resource


@router.get("/resources", response_model=list[ResourceOut])
def list_resources(project: ProjectReader, db: DbSession) -> list[Resource]:
    return list(
        db.scalars(select(Resource).where(Resource.project_id == project.id).order_by(Resource.id))
    )


@router.post("/resources", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(
    body: ResourceCreate, project: ProjectWriter, user: CurrentUser, db: DbSession
) -> Resource:
    resource = Resource(
        project_id=project.id,
        name=body.name,
        max_units=body.max_units,
        hourly_rate=body.hourly_rate,
    )
    db.add(resource)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un recurso con ese nombre"
        ) from None
    record(
        db,
        user=user,
        project_id=project.id,
        action="create",
        entity="resource",
        entity_id=resource.id,
        changes={"name": body.name, "max_units": body.max_units, "hourly_rate": body.hourly_rate},
    )
    db.commit()
    db.refresh(resource)
    return resource


@router.patch("/resources/{resource_id}", response_model=ResourceOut)
def update_resource(
    resource_id: int, body: ResourceUpdate, project: ProjectWriter, user: CurrentUser, db: DbSession
) -> Resource:
    resource = _get_resource(db, project.id, resource_id)
    changes: dict[str, Any] = {}
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None and getattr(resource, field) != value:
            changes[field] = value
            setattr(resource, field, value)
    if changes:
        record(
            db,
            user=user,
            project_id=project.id,
            action="update",
            entity="resource",
            entity_id=resource.id,
            changes=changes,
        )
    db.commit()
    db.refresh(resource)
    return resource


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: int, project: ProjectWriter, user: CurrentUser, db: DbSession
) -> None:
    resource = _get_resource(db, project.id, resource_id)
    record(
        db,
        user=user,
        project_id=project.id,
        action="delete",
        entity="resource",
        entity_id=resource.id,
        changes={"name": resource.name},
    )
    db.delete(resource)
    db.commit()


@router.get("/assignments", response_model=list[AssignmentOut])
def list_assignments(project: ProjectReader, db: DbSession) -> list[Assignment]:
    return list(
        db.scalars(
            select(Assignment)
            .join(Assignment.resource)
            .where(Resource.project_id == project.id)
            .order_by(Assignment.id)
        )
    )


@router.post(
    "/tasks/{task_id}/assignments",
    response_model=AssignmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    task_id: int, body: AssignmentCreate, project: ProjectWriter, user: CurrentUser, db: DbSession
) -> Assignment:
    get_task_in_project(db, project, task_id)
    _get_resource(db, project.id, body.resource_id)
    assignment = Assignment(
        task_id=task_id, resource_id=body.resource_id, units_percent=body.units_percent
    )
    db.add(assignment)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El recurso ya está asignado a esta tarea"
        ) from None
    record(
        db,
        user=user,
        project_id=project.id,
        action="create",
        entity="assignment",
        entity_id=assignment.id,
        changes={
            "task_id": task_id,
            "resource_id": body.resource_id,
            "units_percent": body.units_percent,
        },
    )
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int, project: ProjectWriter, user: CurrentUser, db: DbSession
) -> None:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or assignment.resource.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asignación no encontrada")
    record(
        db,
        user=user,
        project_id=project.id,
        action="delete",
        entity="assignment",
        entity_id=assignment.id,
        changes={"task_id": assignment.task_id, "resource_id": assignment.resource_id},
    )
    db.delete(assignment)
    db.commit()
