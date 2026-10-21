"""Dependencias entre tareas. No se aceptan ciclos."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import CurrentUser, DbSession, ProjectReader, ProjectWriter, get_task_in_project
from app.models import Dependency as DependencyRow
from app.scheduling import Dependency, check_acyclic
from app.schemas import DependencyCreate, DependencyOut
from app.services.audit import record
from app.services.scheduling import domain_dependencies, list_task_rows

router = APIRouter(prefix="/projects/{project_id}/dependencies", tags=["dependencias"])


@router.get("", response_model=list[DependencyOut])
def list_dependencies(project: ProjectReader, db: DbSession) -> list[DependencyRow]:
    return list(
        db.scalars(
            select(DependencyRow)
            .where(DependencyRow.project_id == project.id)
            .order_by(DependencyRow.id)
        )
    )


@router.post("", response_model=DependencyOut, status_code=status.HTTP_201_CREATED)
def create_dependency(
    body: DependencyCreate, project: ProjectWriter, user: CurrentUser, db: DbSession
) -> DependencyRow:
    get_task_in_project(db, project, body.predecessor_id)
    get_task_in_project(db, project, body.successor_id)

    candidate = Dependency(
        predecessor_id=body.predecessor_id,
        successor_id=body.successor_id,
        type=body.type,
        lag_days=body.lag_days,
    )
    task_ids = [row.id for row in list_task_rows(db, project.id)]
    # Lanza SchedulingError (422) si la nueva dependencia cierra un ciclo.
    check_acyclic(task_ids, [*domain_dependencies(db, project.id), candidate])

    row = DependencyRow(
        project_id=project.id,
        predecessor_id=body.predecessor_id,
        successor_id=body.successor_id,
        type=body.type,
        lag_days=body.lag_days,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Esa dependencia ya existe") from None
    record(
        db,
        user=user,
        project_id=project.id,
        action="create",
        entity="dependency",
        entity_id=row.id,
        changes={
            "predecessor_id": body.predecessor_id,
            "successor_id": body.successor_id,
            "type": body.type,
            "lag_days": body.lag_days,
        },
    )
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dependency(
    dependency_id: int, project: ProjectWriter, user: CurrentUser, db: DbSession
) -> None:
    row = db.get(DependencyRow, dependency_id)
    if row is None or row.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dependencia no encontrada")
    record(
        db,
        user=user,
        project_id=project.id,
        action="delete",
        entity="dependency",
        entity_id=row.id,
        changes={"predecessor_id": row.predecessor_id, "successor_id": row.successor_id},
    )
    db.delete(row)
    db.commit()
