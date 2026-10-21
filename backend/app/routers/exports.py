"""Exportación del proyecto (CSV, XLSX, PDF, JSON) e importación desde el formato JSON."""

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status

from app.deps import CurrentUser, DbSession, ProjectReader
from app.exports.project_json import validate_document
from app.exports.schedule import to_csv, to_xlsx
from app.exports.summary import to_pdf
from app.models import Role
from app.schemas import ProjectOut
from app.services.exports import import_document, project_document, schedule_rows, summary_report
from app.services.scheduling import load_schedule

router = APIRouter(tags=["exportación"])

_CAN_IMPORT = {Role.ADMIN, Role.PROJECT_MANAGER}
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _download(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/projects/{project_id}/export/schedule.csv")
def export_csv(project: ProjectReader, db: DbSession) -> Response:
    rows = schedule_rows(db, project, load_schedule(db, project))
    return _download(to_csv(rows), "text/csv; charset=utf-8", f"cronograma-{project.id}.csv")


@router.get("/projects/{project_id}/export/schedule.xlsx")
def export_xlsx(project: ProjectReader, db: DbSession) -> Response:
    rows = schedule_rows(db, project, load_schedule(db, project))
    return _download(to_xlsx(rows, project.name), _XLSX, f"cronograma-{project.id}.xlsx")


@router.get("/projects/{project_id}/export/summary.pdf")
def export_pdf(project: ProjectReader, db: DbSession, status_date: date | None = None) -> Response:
    report = summary_report(db, project, status_date or date.today())
    return _download(to_pdf(report), "application/pdf", f"resumen-{project.id}.pdf")


@router.get("/projects/{project_id}/export/project.json")
def export_json(project: ProjectReader, db: DbSession) -> dict[str, Any]:
    return project_document(db, project)


@router.post("/projects/import", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def import_project(body: dict[str, Any], user: CurrentUser, db: DbSession) -> Any:
    if user.role not in _CAN_IMPORT:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Solo un project manager o admin importa proyectos"
        )
    errors = validate_document(body)
    if errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)
    return import_document(db, user, body)
