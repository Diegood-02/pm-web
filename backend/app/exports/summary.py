"""Reporte PDF de resumen del proyecto: fechas, ruta crítica, avance y valor ganado."""

import io
from dataclasses import dataclass
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.costing.evm import EvmSummary
from app.exports.schedule import ScheduleRow

_HEADER = colors.HexColor("#1f2937")
_CRITICAL = colors.HexColor("#fde2e2")


@dataclass(frozen=True, slots=True)
class SummaryReport:
    project_name: str
    project_start: date
    project_finish: date
    duration_days: int
    status_date: date
    critical_path: list[str]
    rows: list[ScheduleRow]
    evm: EvmSummary | None


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _ratio(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def to_pdf(report: SummaryReport) -> bytes:
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Resumen del proyecto: {_escape(report.project_name)}", styles["Title"]),
        Paragraph(
            f"Inicio: {report.project_start.isoformat()} · Fin previsto: "
            f"{report.project_finish.isoformat()} · "
            f"Duración: {report.duration_days} días laborables",
            styles["Normal"],
        ),
        Paragraph(f"Fecha de corte: {report.status_date.isoformat()}", styles["Normal"]),
        Spacer(1, 0.4 * cm),
        Paragraph("Ruta crítica", styles["Heading2"]),
    ]
    if report.critical_path:
        story.append(
            Paragraph("; ".join(_escape(name) for name in report.critical_path), styles["Normal"])
        )
    else:
        story.append(Paragraph("Sin tareas críticas.", styles["Normal"]))

    if report.evm is not None:
        story += [Spacer(1, 0.4 * cm), Paragraph("Valor ganado", styles["Heading2"])]
        evm_table = Table(
            [
                ["Presupuesto (BAC)", _money(float(report.evm.bac)), "CPI", _ratio(report.evm.cpi)],
                [
                    "Valor planeado (PV)",
                    _money(float(report.evm.pv)),
                    "SPI",
                    _ratio(report.evm.spi),
                ],
                [
                    "Valor ganado (EV)",
                    _money(float(report.evm.ev)),
                    "Variación costo (CV)",
                    _money(float(report.evm.cv)),
                ],
                [
                    "Costo real (AC)",
                    _money(float(report.evm.ac)),
                    "Variación cronograma (SV)",
                    _money(float(report.evm.sv)),
                ],
            ],
            colWidths=[4.2 * cm, 3.4 * cm, 5.2 * cm, 3.4 * cm],
        )
        evm_table.setStyle(
            TableStyle(
                [("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9)]
            )
        )
        story.append(evm_table)
        if report.evm.cpi_alert or report.evm.spi_alert:
            story.append(Paragraph("<b>Alerta:</b> CPI o SPI por debajo de 0.9.", styles["Normal"]))

    story += [Spacer(1, 0.4 * cm), Paragraph("Cronograma", styles["Heading2"])]
    data = [["WBS", "Tarea", "Inicio", "Fin", "Crítica", "Avance %"]]
    for row in report.rows:
        data.append(
            [
                row.wbs,
                row.name,
                row.start_date.isoformat(),
                row.finish_date.isoformat(),
                "Sí" if row.is_critical else "No",
                str(row.percent_complete),
            ]
        )
    table = Table(
        data, colWidths=[1.6 * cm, 7.4 * cm, 2.6 * cm, 2.6 * cm, 1.8 * cm, 2 * cm], repeatRows=1
    )
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]
    for index, row in enumerate(report.rows, start=1):
        if row.is_critical:
            style.append(("BACKGROUND", (0, index), (-1, index), _CRITICAL))
    table.setStyle(TableStyle(style))
    story.append(table)

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=letter, title=report.project_name, author="PM Web"
    )
    document.build(story)
    return buffer.getvalue()


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
