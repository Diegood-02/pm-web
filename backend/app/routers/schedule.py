"""Cronograma calculado con el motor CPM: fechas, holguras y ruta crítica."""

from fastapi import APIRouter

from app.deps import DbSession, ProjectReader
from app.schemas import ScheduleOut, ScheduleTaskOut
from app.services.scheduling import list_task_rows, load_schedule, task_wbs_codes

router = APIRouter(prefix="/projects/{project_id}/schedule", tags=["cronograma"])


@router.get("", response_model=ScheduleOut)
def get_schedule(project: ProjectReader, db: DbSession) -> ScheduleOut:
    schedule = load_schedule(db, project)
    rows = {row.id: row for row in list_task_rows(db, project.id)}
    codes = task_wbs_codes(list(rows.values()))

    tasks = [
        ScheduleTaskOut(
            task_id=entry.task_id,
            wbs=codes[entry.task_id],
            name=rows[entry.task_id].name,
            is_milestone=rows[entry.task_id].is_milestone,
            duration_days=rows[entry.task_id].duration_days,
            early_start=entry.early_start,
            early_finish=entry.early_finish,
            late_start=entry.late_start,
            late_finish=entry.late_finish,
            total_float=entry.total_float,
            free_float=entry.free_float,
            is_critical=entry.is_critical,
            start_date=entry.start_date,
            finish_date=entry.finish_date,
        )
        for entry in sorted(schedule.tasks.values(), key=lambda e: codes[e.task_id])
    ]
    return ScheduleOut(
        project_id=project.id,
        project_start=schedule.project_start,
        project_finish=schedule.project_finish,
        duration_days=schedule.duration_days,
        critical_path=list(schedule.critical_path),
        tasks=tasks,
    )
