"""Dependencias de FastAPI: usuario autenticado y permisos por proyecto.

Reglas:
- Un usuario sin membresía no puede ver el proyecto: la API responde 404,
  igual que si el proyecto no existiera, para no revelar que existe.
- El rol de proyecto decide qué puede hacer: lector solo lee, miembro edita
  tareas y recursos, project_manager administra el proyecto, la línea base y
  las membresías.
- Un admin global tiene acceso de project_manager en todos los proyectos.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import Project, ProjectMember, Role, Task, User
from app.security import ACCESS_TOKEN, decode_token

_bearer = HTTPBearer(auto_error=False)

_RANK: dict[Role, int] = {Role.READER: 0, Role.MEMBER: 1, Role.PROJECT_MANAGER: 2, Role.ADMIN: 2}


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o expiradas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    user_id = decode_token(credentials.credentials, settings.jwt_secret_key, ACCESS_TOKEN)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def require_project(db: Session, user: User, project_id: int, minimum: Role) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")
    if user.role is Role.ADMIN:
        return project
    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")
    if _RANK[membership.role] < _RANK[minimum]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu rol no permite esta acción")
    return project


def project_reader(project_id: int, user: CurrentUser, db: DbSession) -> Project:
    return require_project(db, user, project_id, Role.READER)


def project_writer(project_id: int, user: CurrentUser, db: DbSession) -> Project:
    return require_project(db, user, project_id, Role.MEMBER)


def project_manager(project_id: int, user: CurrentUser, db: DbSession) -> Project:
    return require_project(db, user, project_id, Role.PROJECT_MANAGER)


ProjectReader = Annotated[Project, Depends(project_reader)]
ProjectWriter = Annotated[Project, Depends(project_writer)]
ProjectManager = Annotated[Project, Depends(project_manager)]


def get_task_in_project(db: Session, project: Project, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")
    return task


def require_admin(user: CurrentUser) -> User:
    if user.role is not Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo un administrador puede hacer esto")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
