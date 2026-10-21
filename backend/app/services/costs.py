"""Puente entre la base de datos y el motor de costos (EVM)."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.costing.evm import TaskEvm, labor_cost, planned_fraction, task_budget
from app.models import Assignment, Project
from app.models import Task as TaskRow
from app.scheduling import Schedule
from app.services.scheduling import list_task_rows, project_calendar, task_wbs_codes


@dataclass(frozen=True, slots=True)
class TaskCostRow:
    """Costos de una tarea, con su código WBS para la vista."""

    wbs: str
    row: TaskRow
    evm: TaskEvm


def task_cost_rows(
    db: Session,
    project: Project,
    schedule: Schedule,
    status_date: date,
) -> list[TaskCostRow]:
    rows = list_task_rows(db, project.id)
    if not rows:
        return []
    codes = task_wbs_codes(rows)
    durations = {row.id: row.duration_days for row in rows}
    assignments = db.scalars(
        select(Assignment).join(Assignment.resource).where(Assignment.task_id.in_(list(durations)))
    )
    labor_by_task: dict[int, list[Decimal]] = defaultdict(list)
    for assignment in assignments:
        labor_by_task[assignment.task_id].append(
            labor_cost(
                assignment.resource.hourly_rate,
                assignment.units_percent,
                project.hours_per_day,
                durations[assignment.task_id],
            )
        )

    calendar = project_calendar(project)
    result: list[TaskCostRow] = []
    for row in sorted(rows, key=lambda r: codes[r.id]):
        entry = schedule.tasks[row.id]
        evm = TaskEvm(
            task_id=row.id,
            budget=task_budget(labor_by_task[row.id], row.fixed_cost),
            planned_fraction=planned_fraction(
                entry.start_date,
                entry.finish_date,
                row.duration_days,
                status_date,
                calendar,
            ),
            percent_complete=row.percent_complete,
            actual_cost=row.actual_cost,
        )
        result.append(TaskCostRow(wbs=codes[row.id], row=row, evm=evm))
    return result
