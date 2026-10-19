"""Registro de auditoría: quién cambió qué y cuándo."""

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record(
    db: Session,
    *,
    user: User | None,
    project_id: int | None,
    action: str,
    entity: str,
    entity_id: int | None,
    changes: dict[str, Any] | None = None,
) -> None:
    """Agrega una entrada a la sesión. Se confirma junto con el cambio que describe."""
    db.add(
        AuditLog(
            project_id=project_id,
            user_id=user.id if user else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            changes=changes or {},
        )
    )
