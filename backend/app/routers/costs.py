"""Costos y valor ganado del proyecto a una fecha de corte."""

from datetime import date

from fastapi import APIRouter

from app.costing.evm import CPI_SPI_THRESHOLD, summarize
from app.deps import DbSession, ProjectReader
from app.schemas import CostReportOut, CostSummaryOut, CostTaskOut
from app.services.costs import task_cost_rows
from app.services.scheduling import load_schedule

router = APIRouter(prefix="/projects/{project_id}/costs", tags=["costos"])


@router.get("", response_model=CostReportOut)
def get_costs(
    project: ProjectReader, db: DbSession, status_date: date | None = None
) -> CostReportOut:
    """Presupuesto, PV, EV, AC, variaciones y CPI/SPI a la fecha de corte.

    Si no se indica `status_date`, se usa la fecha de hoy.
    """
    as_of = status_date or date.today()
    schedule = load_schedule(db, project)
    items = task_cost_rows(db, project, schedule, as_of)
    summary = summarize([item.evm for item in items])
    return CostReportOut(
        project_id=project.id,
        status_date=as_of,
        summary=CostSummaryOut(
            bac=summary.bac,
            pv=summary.pv,
            ev=summary.ev,
            ac=summary.ac,
            cv=float(summary.cv),
            sv=float(summary.sv),
            cpi=summary.cpi,
            spi=summary.spi,
            threshold=float(CPI_SPI_THRESHOLD),
            cpi_alert=summary.cpi_alert,
            spi_alert=summary.spi_alert,
        ),
        tasks=[
            CostTaskOut(
                task_id=item.row.id,
                wbs=item.wbs,
                name=item.row.name,
                budget=item.evm.budget,
                percent_complete=item.evm.percent_complete,
                fixed_cost=item.row.fixed_cost,
                planned_value=item.evm.planned_value,
                earned_value=item.evm.earned_value,
                actual_cost=item.evm.actual_cost,
            )
            for item in items
        ],
    )
