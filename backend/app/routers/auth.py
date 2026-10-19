"""Autenticación: login, refresco de tokens y perfil."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.config import Settings, get_settings
from app.deps import CurrentUser, DbSession
from app.models import User
from app.schemas import LoginRequest, RefreshRequest, TokenPair, UserOut
from app.security import ACCESS_TOKEN, REFRESH_TOKEN, create_token, decode_token, verify_password

router = APIRouter(prefix="/auth", tags=["autenticación"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _issue_pair(user: User, settings: Settings) -> TokenPair:
    return TokenPair(
        access_token=create_token(
            user.id,
            ACCESS_TOKEN,
            timedelta(minutes=settings.jwt_access_token_minutes),
            settings.jwt_secret_key,
        ),
        refresh_token=create_token(
            user.id,
            REFRESH_TOKEN,
            timedelta(days=settings.jwt_refresh_token_days),
            settings.jwt_secret_key,
        ),
    )


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, db: DbSession, settings: SettingsDep) -> TokenPair:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not user.is_active or not verify_password(user.password_hash, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")
    return _issue_pair(user, settings)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: DbSession, settings: SettingsDep) -> TokenPair:
    user_id = decode_token(body.refresh_token, settings.jwt_secret_key, REFRESH_TOKEN)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de refresco inválido")
    return _issue_pair(user, settings)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
