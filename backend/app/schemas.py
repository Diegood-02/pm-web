"""Esquemas Pydantic v2 de entrada y salida de la API."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

from app.models import Role
from app.scheduling import DependencyType

NAME = Field(min_length=1, max_length=200)
# Montos: se reciben y se devuelven como número; internamente son Decimal.
Money = Annotated[
    Decimal,
    Field(ge=0, le=Decimal("1000000000000")),
    PlainSerializer(float, return_type=float, when_used="json"),
]
PASSWORD = Field(min_length=12, max_length=256)


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Autenticación y usuarios ---------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(_Out):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool


class UserCreate(BaseModel):
    """Alta de usuario hecha por un admin (es la invitación)."""

    email: EmailStr
    full_name: str = NAME
    password: str = PASSWORD
    role: Role = Role.MEMBER


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: Role | None = None
    is_active: bool | None = None


# --- Proyectos ------------------------------------------------------------------------


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Zona horaria no válida: {value}") from exc
    return value


def _validate_weekdays(value: list[int]) -> list[int]:
    if not value:
        raise ValueError("Debe haber al menos un día laborable")
    if any(day < 0 or day > 6 for day in value):
        raise ValueError("Los días laborables van de 0 (lunes) a 6 (domingo)")
    return sorted(set(value))


class ProjectCreate(BaseModel):
    name: str = NAME
    description: str = Field(default="", max_length=5000)
    timezone: str | None = None
    start_date: date
    working_weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    hours_per_day: float = Field(default=8.0, gt=0, le=24)
    holidays: list[date] = Field(default_factory=list)
    extra_working_days: list[date] = Field(default_factory=list)

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str | None) -> str | None:
        return None if value is None else _validate_timezone(value)

    @field_validator("working_weekdays")
    @classmethod
    def _check_weekdays(cls, value: list[int]) -> list[int]:
        return _validate_weekdays(value)


class ProjectUpdate(BaseModel):
    """Cambios parciales. `version` es obligatorio para detectar ediciones concurrentes."""

    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    timezone: str | None = None
    start_date: date | None = None
    working_weekdays: list[int] | None = None
    hours_per_day: float | None = Field(default=None, gt=0, le=24)
    holidays: list[date] | None = None
    extra_working_days: list[date] | None = None

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str | None) -> str | None:
        return None if value is None else _validate_timezone(value)

    @field_validator("working_weekdays")
    @classmethod
    def _check_weekdays(cls, value: list[int] | None) -> list[int] | None:
        return None if value is None else _validate_weekdays(value)


class ProjectOut(_Out):
    id: int
    name: str
    description: str
    timezone: str
    start_date: date
    working_weekdays: list[int]
    hours_per_day: float
    holidays: list[date]
    extra_working_days: list[date]
    version: int
    created_at: datetime
    updated_at: datetime


class MemberCreate(BaseModel):
    user_id: int
    role: Role


class MemberUpdate(BaseModel):
    role: Role


class MemberOut(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: Role


# --- Tareas ---------------------------------------------------------------------------


class TaskCreate(BaseModel):
    name: str = NAME
    duration_days: int = Field(default=0, ge=0, le=100_000)
    is_milestone: bool = False
    parent_id: int | None = None
    fixed_cost: Money = Decimal("0")

    @model_validator(mode="after")
    def _milestone_has_no_duration(self) -> "TaskCreate":
        if self.is_milestone and self.duration_days != 0:
            raise ValueError("Un hito debe tener duración 0")
        return self


class TaskUpdate(BaseModel):
    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    duration_days: int | None = Field(default=None, ge=0, le=100_000)
    is_milestone: bool | None = None
    fixed_cost: Money | None = None
    actual_cost: Money | None = None
    percent_complete: int | None = Field(default=None, ge=0, le=100)


class TaskMove(BaseModel):
    """Mueve una tarea en el WBS: nuevo padre y posición entre sus hermanas."""

    version: int = Field(ge=1)
    parent_id: int | None = None
    position: int = Field(ge=0)


class TaskOut(_Out):
    id: int
    parent_id: int | None
    wbs: str
    position: int
    name: str
    duration_days: int
    is_milestone: bool
    fixed_cost: Money
    actual_cost: Money
    percent_complete: int
    version: int


# --- Dependencias ---------------------------------------------------------------------


class DependencyCreate(BaseModel):
    predecessor_id: int
    successor_id: int
    type: DependencyType = DependencyType.FS
    lag_days: int = Field(default=0, ge=-100_000, le=100_000)

    @model_validator(mode="after")
    def _not_self(self) -> "DependencyCreate":
        if self.predecessor_id == self.successor_id:
            raise ValueError("Una tarea no puede depender de sí misma")
        return self


class DependencyOut(_Out):
    id: int
    predecessor_id: int
    successor_id: int
    type: DependencyType
    lag_days: int


# --- Recursos y asignaciones ----------------------------------------------------------


class ResourceCreate(BaseModel):
    name: str = NAME
    max_units: int = Field(default=100, ge=1, le=1000)
    hourly_rate: Money = Decimal("0")


class ResourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    max_units: int | None = Field(default=None, ge=1, le=1000)
    hourly_rate: Money | None = None


class ResourceOut(_Out):
    id: int
    name: str
    max_units: int
    hourly_rate: Money


class AssignmentCreate(BaseModel):
    resource_id: int
    units_percent: int = Field(ge=1, le=1000)


class AssignmentOut(_Out):
    id: int
    task_id: int
    resource_id: int
    units_percent: int


# --- Línea base y cronograma ----------------------------------------------------------


class BaselineCreate(BaseModel):
    name: str = NAME


class BaselineSummary(_Out):
    id: int
    name: str
    created_at: datetime
    project_finish: date
    duration_days: int


class BaselineTaskOut(_Out):
    task_id: int | None
    wbs: str
    name: str
    is_milestone: bool
    duration_days: int
    start_offset: int
    finish_offset: int
    start_date: date
    finish_date: date
    budget: Money


class BaselineDetail(BaselineSummary):
    tasks: list[BaselineTaskOut]


class BaselineVariance(BaseModel):
    """Variaciones en días laborables: positivo = el plan actual va después de la línea base."""

    task_id: int | None
    wbs: str
    name: str
    baseline_start: date
    baseline_finish: date
    current_start: date | None
    current_finish: date | None
    start_variance_days: int | None
    finish_variance_days: int | None


class ScheduleTaskOut(BaseModel):
    task_id: int
    wbs: str
    name: str
    is_milestone: bool
    duration_days: int
    early_start: int
    early_finish: int
    late_start: int
    late_finish: int
    total_float: int
    free_float: int
    is_critical: bool
    start_date: date
    finish_date: date


class ScheduleOut(BaseModel):
    project_id: int
    project_start: date
    project_finish: date
    duration_days: int
    critical_path: list[int]
    tasks: list[ScheduleTaskOut]


# --- Auditoría ------------------------------------------------------------------------


# --- Costos y valor ganado ------------------------------------------------------------


class CostTaskOut(BaseModel):
    task_id: int
    wbs: str
    name: str
    budget: Money
    percent_complete: int
    fixed_cost: Money
    planned_value: Money
    earned_value: Money
    actual_cost: Money


class CostSummaryOut(BaseModel):
    bac: Money
    pv: Money
    ev: Money
    ac: Money
    cv: float
    sv: float
    cpi: float | None
    spi: float | None
    threshold: float
    cpi_alert: bool
    spi_alert: bool


class CostReportOut(BaseModel):
    project_id: int
    status_date: date
    summary: CostSummaryOut
    tasks: list[CostTaskOut]


class AuditLogOut(_Out):
    id: int
    user_id: int | None
    action: str
    entity: str
    entity_id: int | None
    changes: dict[str, Any]
    created_at: datetime
