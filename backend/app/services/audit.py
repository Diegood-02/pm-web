"""Registro de auditoría: quién cambió qué y cuándo."""

import json
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def _json_default(value: object) -> object:
    """Convierte tipos que JSON no soporta: montos a número y fechas a ISO 8601."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


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
            changes=json.loads(json.dumps(changes or {}, default=_json_default)),
        )
    )
