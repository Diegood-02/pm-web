"""Líneas base: copia del cronograma en un momento y comparación contra el plan actual."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession, ProjectManager, ProjectReader
from app.models import Baseline, BaselineTask
from app.schemas import (
    BaselineCreate,
    BaselineDetail,
    BaselineSummary,
    BaselineVariance,
)
from app.services.audit import record
from app.services.scheduling import list_task_rows, load_schedule, task_wbs_codes

router = APIRouter(prefix="/projects/{project_id}/baselines", tags=["línea base"])


def _get_baseline(db: DbSession, project_id: int, baseline_id: int) -> Baseline:
    baseline = db.get(Baseline, baseline_id)
    if baseline is None or baseline.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Línea base no encontrada")
    return baseline


@router.get("", response_model=list[BaselineSummary])
def list_baselines(project: ProjectReader, db: DbSession) -> list[Baseline]:
    return list(
        db.scalars(select(Baseline).where(Baseline.project_id == project.id).order_by(Baseline.id))
    )


@router.post("", response_model=BaselineDetail, status_code=status.HTTP_201_CREATED)
def create_baseline(
    body: BaselineCreate, project: ProjectManager, user: CurrentUser, db: DbSession
) -> Baseline:
    schedule = load_schedule(db, project)
    rows = list_task_rows(db, project.id)
    codes = task_wbs_codes(rows)

    baseline = Baseline(
        project_id=project.id,
        name=body.name,
        created_by_id=user.id,
        project_finish=schedule.project_finish,
        duration_days=schedule.duration_days,
    )
    for row in rows:
        entry = schedule.tasks[row.id]
        baseline.tasks.append(
            BaselineTask(
                task_id=row.id,
                wbs=codes[row.id],
                name=row.name,
                is_milestone=row.is_milestone,
                duration_days=row.duration_days,
                start_offset=entry.early_start,
                finish_offset=entry.early_finish,
                start_date=entry.start_date,
                finish_date=entry.finish_date,
            )
        )
    db.add(baseline)
    db.flush()
    record(
        db,
        user=user,
        project_id=project.id,
        action="create",
        entity="baseline",
        entity_id=baseline.id,
        changes={"name": body.name, "tasks": len(rows)},
    )
    db.commit()
    db.refresh(baseline)
    return baseline


@router.get("/{baseline_id}", response_model=BaselineDetail)
def get_baseline(baseline_id: int, project: ProjectReader, db: DbSession) -> Baseline:
    return _get_baseline(db, project.id, baseline_id)


@router.get("/{baseline_id}/comparison", response_model=list[BaselineVariance])
def compare_baseline(
    baseline_id: int, project: ProjectReader, db: DbSession
) -> list[BaselineVariance]:
    """Compara cada tarea de la línea base con el plan actual, en días laborables."""
    baseline = _get_baseline(db, project.id, baseline_id)
    current = load_schedule(db, project)

    result: list[BaselineVariance] = []
    for entry in baseline.tasks:
        now = current.tasks.get(entry.task_id) if entry.task_id is not None else None
        result.append(
            BaselineVariance(
                task_id=entry.task_id,
                wbs=entry.wbs,
                name=entry.name,
                baseline_start=entry.start_date,
                baseline_finish=entry.finish_date,
                current_start=now.start_date if now else None,
                current_finish=now.finish_date if now else None,
                start_variance_days=now.early_start - entry.start_offset if now else None,
                finish_variance_days=now.early_finish - entry.finish_offset if now else None,
            )
        )
    return result
