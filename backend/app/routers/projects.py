"""Proyectos y membresías por proyecto."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.deps import CurrentUser, DbSession, ProjectManager, ProjectReader
from app.models import Project, ProjectMember, Role, User
from app.schemas import (
    MemberCreate,
    MemberOut,
    MemberUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
)
from app.services.audit import record

router = APIRouter(prefix="/projects", tags=["proyectos"])

_CAN_CREATE_PROJECTS = {Role.ADMIN, Role.PROJECT_MANAGER}


def _iso(values: list[Any]) -> list[str]:
    return [value.isoformat() for value in values]


@router.get("", response_model=list[ProjectOut])
def list_projects(user: CurrentUser, db: DbSession) -> list[Project]:
    """Solo devuelve los proyectos donde el usuario es miembro (los admins ven todos)."""
    query = select(Project).order_by(Project.id)
    if user.role is not Role.ADMIN:
        query = query.join(ProjectMember).where(ProjectMember.user_id == user.id)
    return list(db.scalars(query))


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, user: CurrentUser, db: DbSession) -> Project:
    if user.role not in _CAN_CREATE_PROJECTS:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Solo un project manager o admin crea proyectos"
        )
    project = Project(
        name=body.name,
        description=body.description,
        created_by_id=user.id,
        timezone=body.timezone or get_settings().default_timezone,
        start_date=body.start_date,
        working_weekdays=body.working_weekdays,
        hours_per_day=body.hours_per_day,
        holidays=_iso(body.holidays),
        extra_working_days=_iso(body.extra_working_days),
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role=Role.PROJECT_MANAGER))
    record(
        db,
        user=user,
        project_id=project.id,
        action="create",
        entity="project",
        entity_id=project.id,
        changes={"name": project.name},
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: ProjectReader) -> Project:
    return project


_FIELDS_AS_ISO = {"holidays", "extra_working_days"}


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    body: ProjectUpdate, project: ProjectManager, user: CurrentUser, db: DbSession
) -> Project:
    if body.version != project.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El proyecto fue modificado por otra persona. Recarga antes de guardar.",
        )
    changes: dict[str, Any] = {}
    for field, value in body.model_dump(exclude_unset=True, exclude={"version"}).items():
        if value is None:
            continue
        if field in _FIELDS_AS_ISO:
            value = _iso(value)
        if getattr(project, field) != value:
            changes[field] = value
            setattr(project, field, value)
    if changes:
        project.version += 1
        record(
            db,
            user=user,
            project_id=project.id,
            action="update",
            entity="project",
            entity_id=project.id,
            changes=changes,
        )
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project: ProjectManager, user: CurrentUser, db: DbSession) -> None:
    record(
        db,
        user=user,
        project_id=None,
        action="delete",
        entity="project",
        entity_id=project.id,
        changes={"name": project.name},
    )
    db.delete(project)
    db.commit()


# --- Membresías -----------------------------------------------------------------------


def _member_out(membership: ProjectMember) -> MemberOut:
    return MemberOut(
        user_id=membership.user_id,
        email=membership.user.email,
        full_name=membership.user.full_name,
        role=membership.role,
    )


def _project_manager_count(db: DbSession, project_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.role == Role.PROJECT_MANAGER,
            )
        )
        or 0
    )


@router.get("/{project_id}/members", response_model=list[MemberOut])
def list_members(project: ProjectReader, db: DbSession) -> list[MemberOut]:
    memberships = db.scalars(
        select(ProjectMember)
        .where(ProjectMember.project_id == project.id)
        .order_by(ProjectMember.id)
    )
    return [_member_out(m) for m in memberships]


@router.post(
    "/{project_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    body: MemberCreate, project: ProjectManager, user: CurrentUser, db: DbSession
) -> MemberOut:
    target = db.get(User, body.user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    if body.role is Role.ADMIN:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "admin no es un rol de proyecto")
    membership = ProjectMember(project_id=project.id, user_id=target.id, role=body.role)
    db.add(membership)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El usuario ya es miembro del proyecto"
        ) from None
    record(
        db,
        user=user,
        project_id=project.id,
        action="add_member",
        entity="membership",
        entity_id=target.id,
        changes={"role": body.role},
    )
    db.commit()
    db.refresh(membership)
    return _member_out(membership)


def _get_membership(db: DbSession, project_id: int, user_id: int) -> ProjectMember:
    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Miembro no encontrado")
    return membership


@router.patch("/{project_id}/members/{user_id}", response_model=MemberOut)
def update_member(
    user_id: int, body: MemberUpdate, project: ProjectManager, user: CurrentUser, db: DbSession
) -> MemberOut:
    membership = _get_membership(db, project.id, user_id)
    if body.role is Role.ADMIN:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "admin no es un rol de proyecto")
    if (
        membership.role is Role.PROJECT_MANAGER
        and body.role is not Role.PROJECT_MANAGER
        and _project_manager_count(db, project.id) == 1
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "El proyecto debe tener un project manager"
        )
    if membership.role != body.role:
        record(
            db,
            user=user,
            project_id=project.id,
            action="update_member",
            entity="membership",
            entity_id=user_id,
            changes={"from": membership.role, "to": body.role},
        )
        membership.role = body.role
    db.commit()
    db.refresh(membership)
    return _member_out(membership)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(user_id: int, project: ProjectManager, user: CurrentUser, db: DbSession) -> None:
    membership = _get_membership(db, project.id, user_id)
    if membership.role is Role.PROJECT_MANAGER and _project_manager_count(db, project.id) == 1:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "El proyecto debe tener un project manager"
        )
    record(
        db,
        user=user,
        project_id=project.id,
        action="remove_member",
        entity="membership",
        entity_id=user_id,
        changes={"role": membership.role},
    )
    db.delete(membership)
    db.commit()
