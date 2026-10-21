"""Reúne los datos de un proyecto para exportarlo y crea proyectos desde un documento importado."""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.costing.evm import summarize
from app.exports.project_json import build_document
from app.exports.schedule import ScheduleRow
from app.exports.summary import SummaryReport
from app.models import Assignment, Dependency, Project, ProjectMember, Resource, Role, Task, User
from app.scheduling import Schedule
from app.services.audit import record
from app.services.costs import task_cost_rows
from app.services.scheduling import list_task_rows, load_schedule, ordered_tasks


def schedule_rows(db: Session, project: Project, schedule: Schedule) -> list[ScheduleRow]:
    rows = list_task_rows(db, project.id)
    by_id = {row.id: row for row in rows}
    result: list[ScheduleRow] = []
    for node in ordered_tasks(rows):
        entry = schedule.tasks[node.row.id]
        result.append(
            ScheduleRow(
                wbs=node.wbs,
                name=node.row.name,
                is_milestone=node.row.is_milestone,
                duration_days=node.row.duration_days,
                start_date=entry.start_date,
                finish_date=entry.finish_date,
                total_float=entry.total_float,
                free_float=entry.free_float,
                is_critical=entry.is_critical,
                percent_complete=by_id[node.row.id].percent_complete,
            )
        )
    return result


def summary_report(db: Session, project: Project, status_date: date) -> SummaryReport:
    schedule = load_schedule(db, project)
    rows = schedule_rows(db, project, schedule)
    names = {
        node.row.id: f"{node.wbs} {node.row.name}"
        for node in ordered_tasks(list_task_rows(db, project.id))
    }
    items = task_cost_rows(db, project, schedule, status_date)
    evm = summarize([item.evm for item in items]) if items else None
    return SummaryReport(
        project_name=project.name,
        project_start=schedule.project_start,
        project_finish=schedule.project_finish,
        duration_days=schedule.duration_days,
        status_date=status_date,
        critical_path=[names[task_id] for task_id in schedule.critical_path],
        rows=rows,
        evm=evm,
    )


def project_document(db: Session, project: Project) -> dict[str, Any]:
    rows = list_task_rows(db, project.id)
    tasks = [
        {
            "id": node.row.id,
            "parent_id": node.row.parent_id,
            "name": node.row.name,
            "duration_days": node.row.duration_days,
            "is_milestone": node.row.is_milestone,
            "fixed_cost": node.row.fixed_cost,
            "actual_cost": node.row.actual_cost,
            "percent_complete": node.row.percent_complete,
        }
        for node in ordered_tasks(rows)
    ]
    resources = list(
        db.scalars(select(Resource).where(Resource.project_id == project.id).order_by(Resource.id))
    )
    dependencies = list(
        db.scalars(
            select(Dependency).where(Dependency.project_id == project.id).order_by(Dependency.id)
        )
    )
    assignments = list(
        db.scalars(
            select(Assignment)
            .join(Assignment.resource)
            .where(Resource.project_id == project.id)
            .order_by(Assignment.id)
        )
    )
    return build_document(
        project={
            "name": project.name,
            "description": project.description,
            "timezone": project.timezone,
            "start_date": project.start_date.isoformat(),
            "working_weekdays": project.working_weekdays,
            "hours_per_day": project.hours_per_day,
            "holidays": project.holidays,
            "extra_working_days": project.extra_working_days,
        },
        tasks=tasks,
        resources_list=[
            {"id": r.id, "name": r.name, "max_units": r.max_units, "hourly_rate": r.hourly_rate}
            for r in resources
        ],
        dependencies=[
            {
                "predecessor_id": d.predecessor_id,
                "successor_id": d.successor_id,
                "type": d.type.value,
                "lag_days": d.lag_days,
            }
            for d in dependencies
        ],
        assignments=[
            {"task_id": a.task_id, "resource_id": a.resource_id, "units_percent": a.units_percent}
            for a in assignments
        ],
    )


def import_document(db: Session, user: User, doc: dict[str, Any]) -> Project:
    """Crea el proyecto y su contenido. Asume que el documento ya pasó la validación."""
    meta = doc["project"]
    project = Project(
        name=meta["name"],
        description=meta.get("description", ""),
        created_by_id=user.id,
        timezone=meta.get("timezone") or get_settings().default_timezone,
        start_date=date.fromisoformat(meta["start_date"]),
        working_weekdays=sorted(meta.get("working_weekdays", [0, 1, 2, 3, 4])),
        hours_per_day=float(meta.get("hours_per_day", 8)),
        holidays=sorted(meta.get("holidays", [])),
        extra_working_days=sorted(meta.get("extra_working_days", [])),
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role=Role.PROJECT_MANAGER))

    resource_ids: dict[str, int] = {}
    for item in doc["resources"]:
        resource = Resource(
            project_id=project.id,
            name=item["name"],
            max_units=item.get("max_units", 100),
            hourly_rate=item.get("hourly_rate", 0),
        )
        db.add(resource)
        db.flush()
        resource_ids[item["ref"]] = resource.id

    # Primero se crean todas las tareas sin padre y luego se enlazan;
    # así el orden del documento no importa.
    task_ids: dict[str, int] = {}
    positions: dict[str | None, int] = {}
    for item in doc["tasks"]:
        is_milestone = item.get("is_milestone", False)
        task = Task(
            project_id=project.id,
            parent_id=None,
            position=positions.get(item.get("parent_ref"), 0),
            name=item["name"],
            duration_days=0 if is_milestone else item["duration_days"],
            is_milestone=is_milestone,
            fixed_cost=item.get("fixed_cost", 0),
            actual_cost=item.get("actual_cost", 0),
            percent_complete=item.get("percent_complete", 0),
        )
        positions[item.get("parent_ref")] = positions.get(item.get("parent_ref"), 0) + 1
        db.add(task)
        db.flush()
        task_ids[item["ref"]] = task.id
    for item in doc["tasks"]:
        if item.get("parent_ref") is not None:
            linked = db.get(Task, task_ids[item["ref"]])
            assert linked is not None
            linked.parent_id = task_ids[item["parent_ref"]]

    for item in doc["dependencies"]:
        db.add(
            Dependency(
                project_id=project.id,
                predecessor_id=task_ids[item["predecessor_ref"]],
                successor_id=task_ids[item["successor_ref"]],
                type=item.get("type", "FS"),
                lag_days=item.get("lag_days", 0),
            )
        )
    for item in doc["assignments"]:
        db.add(
            Assignment(
                task_id=task_ids[item["task_ref"]],
                resource_id=resource_ids[item["resource_ref"]],
                units_percent=item["units_percent"],
            )
        )
    db.flush()
    record(
        db,
        user=user,
        project_id=project.id,
        action="import",
        entity="project",
        entity_id=project.id,
        changes={"tasks": len(doc["tasks"]), "dependencies": len(doc["dependencies"])},
    )
    db.commit()
    db.refresh(project)
    return project
