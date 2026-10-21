"""Consulta del registro de auditoría de un proyecto (solo project manager)."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.deps import DbSession, ProjectManager
from app.models import AuditLog
from app.schemas import AuditLogOut

router = APIRouter(prefix="/projects/{project_id}/audit", tags=["auditoría"])


@router.get("", response_model=list[AuditLogOut])
def list_audit(
    project: ProjectManager,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.project_id == project.id)
            .order_by(AuditLog.id.desc())
            .limit(limit)
        )
    )
