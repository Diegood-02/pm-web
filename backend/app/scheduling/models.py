"""Modelos de dominio del motor de programación.

Son dataclasses inmutables, sin dependencias de base de datos ni de FastAPI.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class DependencyType(StrEnum):
    """Tipo de relación entre predecesora y sucesora."""

    FS = "FS"  # fin a inicio
    SS = "SS"  # inicio a inicio
    FF = "FF"  # fin a fin
    SF = "SF"  # inicio a fin


@dataclass(frozen=True, slots=True)
class Task:
    """Tarea del cronograma. La duración se expresa en días laborables."""

    id: int
    name: str
    duration_days: int
    wbs: str = ""
    is_milestone: bool = False

    def __post_init__(self) -> None:
        if self.duration_days < 0:
            raise ValueError(f"La duración de la tarea {self.id} no puede ser negativa")
        if self.is_milestone and self.duration_days != 0:
            raise ValueError(f"El hito {self.id} debe tener duración 0")


@dataclass(frozen=True, slots=True)
class Dependency:
    """Relación entre dos tareas. El retraso (lag) está en días laborables y puede ser negativo."""

    predecessor_id: int
    successor_id: int
    type: DependencyType = DependencyType.FS
    lag_days: int = 0

    def __post_init__(self) -> None:
        if self.predecessor_id == self.successor_id:
            raise ValueError(f"La tarea {self.predecessor_id} no puede depender de sí misma")


@dataclass(frozen=True, slots=True)
class Calendar:
    """Calendario laboral.

    working_weekdays: días de la semana laborables (0 = lunes ... 6 = domingo).
    holidays: fechas no laborables (feriados).
    extra_working_days: fechas laborables excepcionales (p. ej. sábado de entrega).
        Si una fecha está en ambos conjuntos, gana la excepción laborable.
    hours_per_day: horas de trabajo por día; se usará en costos (Fase 4).
    """

    working_weekdays: frozenset[int] = frozenset({0, 1, 2, 3, 4})
    hours_per_day: float = 8.0
    holidays: frozenset[date] = frozenset()
    extra_working_days: frozenset[date] = frozenset()

    def __post_init__(self) -> None:
        if not self.working_weekdays:
            raise ValueError("El calendario necesita al menos un día laborable de la semana")
        if not all(0 <= weekday <= 6 for weekday in self.working_weekdays):
            raise ValueError("working_weekdays debe contener valores entre 0 y 6")
        if self.hours_per_day <= 0:
            raise ValueError("hours_per_day debe ser mayor que cero")

    def is_working_day(self, day: date) -> bool:
        if day in self.extra_working_days:
            return True
        return day.weekday() in self.working_weekdays and day not in self.holidays

    def working_days_from(self, start: date) -> Iterator[date]:
        """Genera, en orden, los días laborables a partir de `start` (incluido)."""
        day = start
        while True:
            if self.is_working_day(day):
                yield day
            day += timedelta(days=1)
