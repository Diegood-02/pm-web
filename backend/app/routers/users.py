"""Gestión de usuarios (solo admin). Dar de alta un usuario equivale a invitarlo."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import AdminUser, DbSession
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate
from app.security import hash_password
from app.services.audit import record

router = APIRouter(prefix="/users", tags=["usuarios"])


@router.get("", response_model=list[UserOut])
def list_users(
    _: AdminUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, admin: AdminUser, db: DbSession) -> User:
    email = body.email.lower()
    user = User(
        email=email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un usuario con ese correo"
        ) from None
    record(
        db,
        user=admin,
        project_id=None,
        action="create",
        entity="user",
        entity_id=user.id,
        changes={"email": email, "role": body.role},
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, admin: AdminUser, db: DbSession) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    if user.id == admin.id and body.is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes desactivarte a ti mismo")

    changes: dict[str, object] = {}
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        if getattr(user, field) != value:
            changes[field] = value
            setattr(user, field, value)
    if changes:
        record(
            db,
            user=admin,
            project_id=None,
            action="update",
            entity="user",
            entity_id=user.id,
            changes=changes,
        )
    db.commit()
    db.refresh(user)
    return user
