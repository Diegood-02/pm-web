"""Costos y valor ganado (EVM). Funciones puras, sin base de datos ni FastAPI.

Convenciones:
- Montos en Decimal. Los índices (CPI, SPI) son float redondeados a 4 decimales.
- Costo de mano de obra de una asignación:
    tarifa_por_hora * (unidades / 100) * horas_por_día * duración_en_días
- Presupuesto de una tarea (BAC de la tarea) = suma de mano de obra + costo fijo.
- Valor planeado (PV): avance temporal lineal del presupuesto sobre los días laborables
  de la tarea. Un hito vale todo su presupuesto al llegar a su fecha.
- Valor ganado (EV): presupuesto * porcentaje completado.
- Costo real (AC): capturado por tarea.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.scheduling import Calendar

CPI_SPI_THRESHOLD = Decimal("0.9")
MONEY_QUANT = Decimal("0.01")
RATIO_QUANT = Decimal("0.0001")
_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


def labor_cost(
    hourly_rate: Decimal,
    units_percent: int,
    hours_per_day: float,
    duration_days: int,
) -> Decimal:
    """Costo de mano de obra de una asignación a lo largo de la duración de la tarea."""
    hours = Decimal(str(hours_per_day)) * Decimal(duration_days)
    dedication = Decimal(units_percent) / _HUNDRED
    return _money(hourly_rate * dedication * hours)


def task_budget(labor_costs: Iterable[Decimal], fixed_cost: Decimal) -> Decimal:
    """Presupuesto de una tarea: mano de obra de todas sus asignaciones más el costo fijo."""
    return _money(sum(labor_costs, _ZERO) + fixed_cost)


def planned_fraction(
    start: date,
    finish: date,
    duration_days: int,
    status_date: date,
    calendar: Calendar,
) -> Decimal:
    """Fracción del presupuesto que debería estar ejecutada en `status_date` (entre 0 y 1)."""
    if status_date < start:
        return _ZERO
    if duration_days == 0:
        return Decimal("1") if status_date >= finish else _ZERO
    if status_date >= finish:
        return Decimal("1")
    elapsed = _working_days_between(start, status_date, calendar)
    return min(Decimal("1"), Decimal(elapsed) / Decimal(duration_days))


@dataclass(frozen=True, slots=True)
class TaskEvm:
    task_id: int
    budget: Decimal
    planned_fraction: Decimal
    percent_complete: int
    actual_cost: Decimal

    @property
    def planned_value(self) -> Decimal:
        return _money(self.budget * self.planned_fraction)

    @property
    def earned_value(self) -> Decimal:
        return _money(self.budget * Decimal(self.percent_complete) / _HUNDRED)


@dataclass(frozen=True, slots=True)
class EvmSummary:
    bac: Decimal
    pv: Decimal
    ev: Decimal
    ac: Decimal
    cv: Decimal
    sv: Decimal
    cpi: float | None
    spi: float | None
    cpi_alert: bool
    spi_alert: bool


def summarize(items: Sequence[TaskEvm]) -> EvmSummary:
    bac = _money(sum((item.budget for item in items), _ZERO))
    pv = _money(sum((item.planned_value for item in items), _ZERO))
    ev = _money(sum((item.earned_value for item in items), _ZERO))
    ac = _money(sum((item.actual_cost for item in items), _ZERO))
    cpi = _ratio(ev, ac)
    spi = _ratio(ev, pv)
    return EvmSummary(
        bac=bac,
        pv=pv,
        ev=ev,
        ac=ac,
        cv=_money(ev - ac),
        sv=_money(ev - pv),
        cpi=cpi,
        spi=spi,
        cpi_alert=cpi is not None and Decimal(str(cpi)) < CPI_SPI_THRESHOLD,
        spi_alert=spi is not None and Decimal(str(spi)) < CPI_SPI_THRESHOLD,
    )


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _ratio(numerator: Decimal, denominator: Decimal) -> float | None:
    if denominator == _ZERO:
        return None
    return float((numerator / denominator).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP))


def _working_days_between(start: date, end: date, calendar: Calendar) -> int:
    """Días laborables entre dos fechas, ambas incluidas."""
    count = 0
    day = start
    while day <= end:
        if calendar.is_working_day(day):
            count += 1
        day += timedelta(days=1)
    return count
