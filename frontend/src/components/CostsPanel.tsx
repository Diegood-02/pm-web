import { useEffect, useState } from "react";

import { api } from "../api/endpoints";
import type { CostReport, CostTask, Task } from "../api/types";

// Moneda de presentación. Los montos del backend no llevan moneda; el proyecto se
// configura en MXN porque la zona horaria por defecto es America/Mexico_City.
const CURRENCY = "MXN";
const money = new Intl.NumberFormat("es-MX", { style: "currency", currency: CURRENCY });
const ratio = (value: number | null) => (value === null ? "—" : value.toFixed(4));

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

interface CostsPanelProps {
  projectId: number;
  tasks: Task[];
  canEdit: boolean;
  /** Cambia cuando los datos del proyecto se recargan, para recalcular los costos. */
  stamp: unknown;
  onAction: (action: () => Promise<unknown>, fallback: string) => Promise<void>;
}

export function CostsPanel({ projectId, tasks, canEdit, stamp, onAction }: CostsPanelProps) {
  const [statusDate, setStatusDate] = useState(todayIso);
  const [report, setReport] = useState<CostReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .costs(projectId, statusDate)
      .then((result) => {
        if (active) {
          setReport(result);
          setError(null);
        }
      })
      .catch(() => {
        if (active) setError("No se pudieron calcular los costos para esa fecha.");
      });
    return () => {
      active = false;
    };
  }, [projectId, statusDate, stamp]);

  if (error)
    return (
      <p role="alert" className="error">
        {error}
      </p>
    );
  if (!report) return <p role="status">Calculando costos…</p>;

  const { summary } = report;
  const versionById = new Map(tasks.map((task) => [task.id, task.version]));

  return (
    <section aria-labelledby="titulo-costos">
      <h2 id="titulo-costos">Costos y valor ganado</h2>

      <div className="field">
        <label htmlFor="cost-status-date">Fecha de corte</label>
        <input
          id="cost-status-date"
          type="date"
          value={statusDate}
          onChange={(event) => setStatusDate(event.target.value)}
        />
      </div>

      {(summary.cpi_alert || summary.spi_alert) && (
        <div role="alert" className="alert">
          <strong>Alerta de desempeño.</strong>{" "}
          {summary.cpi_alert &&
            `CPI ${ratio(summary.cpi)} está por debajo de ${summary.threshold}. `}
          {summary.spi_alert &&
            `SPI ${ratio(summary.spi)} está por debajo de ${summary.threshold}.`}
        </div>
      )}

      <dl className="cost-cards">
        <div>
          <dt>Presupuesto (BAC)</dt>
          <dd>{money.format(summary.bac)}</dd>
        </div>
        <div>
          <dt>Valor planeado (PV)</dt>
          <dd>{money.format(summary.pv)}</dd>
        </div>
        <div>
          <dt>Valor ganado (EV)</dt>
          <dd>{money.format(summary.ev)}</dd>
        </div>
        <div>
          <dt>Costo real (AC)</dt>
          <dd>{money.format(summary.ac)}</dd>
        </div>
        <div>
          <dt>Variación de costo (CV)</dt>
          <dd>{money.format(summary.cv)}</dd>
        </div>
        <div>
          <dt>Variación de cronograma (SV)</dt>
          <dd>{money.format(summary.sv)}</dd>
        </div>
        <div className={summary.cpi_alert ? "bad" : undefined}>
          <dt>CPI</dt>
          <dd>{ratio(summary.cpi)}</dd>
        </div>
        <div className={summary.spi_alert ? "bad" : undefined}>
          <dt>SPI</dt>
          <dd>{ratio(summary.spi)}</dd>
        </div>
      </dl>

      <table>
        <caption className="sr-only">Costos por tarea a la fecha de corte</caption>
        <thead>
          <tr>
            <th scope="col">WBS</th>
            <th scope="col">Tarea</th>
            <th scope="col">Presupuesto</th>
            <th scope="col">Costo fijo</th>
            <th scope="col">Avance (%)</th>
            <th scope="col">PV</th>
            <th scope="col">EV</th>
            <th scope="col">Costo real</th>
          </tr>
        </thead>
        <tbody>
          {report.tasks.map((row) => (
            <CostRow
              key={`${row.task_id}-${versionById.get(row.task_id) ?? 0}`}
              row={row}
              version={versionById.get(row.task_id) ?? 1}
              projectId={projectId}
              canEdit={canEdit}
              onAction={onAction}
            />
          ))}
          {report.tasks.length === 0 && (
            <tr>
              <td colSpan={8}>No hay tareas con costos todavía.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

interface CostRowProps {
  row: CostTask;
  version: number;
  projectId: number;
  canEdit: boolean;
  onAction: CostsPanelProps["onAction"];
}

function CostRow({ row, version, projectId, canEdit, onAction }: CostRowProps) {
  const [percent, setPercent] = useState(String(row.percent_complete));
  const [actual, setActual] = useState(String(row.actual_cost));
  const [fixed, setFixed] = useState(String(row.fixed_cost));

  function commit(
    raw: string,
    current: number,
    field: "percent_complete" | "actual_cost" | "fixed_cost",
    setDraft: (value: string) => void,
    max: number | null,
  ) {
    const value = Number(raw);
    const valid =
      raw.trim() !== "" && Number.isFinite(value) && value >= 0 && (max === null || value <= max);
    if (!valid) {
      setDraft(String(current));
      return;
    }
    if (value === current) return;
    void onAction(
      () => api.updateTask(projectId, row.task_id, { version, [field]: value }),
      "No se pudo guardar el cambio.",
    );
  }

  return (
    <tr>
      <th scope="row">{row.wbs}</th>
      <td>{row.name}</td>
      <td>{money.format(row.budget)}</td>
      <td>
        {canEdit ? (
          <>
            <label className="sr-only" htmlFor={`fixed-${row.task_id}`}>
              Costo fijo de {row.name}
            </label>
            <input
              id={`fixed-${row.task_id}`}
              type="number"
              min={0}
              step="0.01"
              className="money"
              value={fixed}
              onChange={(event) => setFixed(event.target.value)}
              onBlur={() => commit(fixed, row.fixed_cost, "fixed_cost", setFixed, null)}
            />
          </>
        ) : (
          money.format(row.fixed_cost)
        )}
      </td>
      <td>
        {canEdit ? (
          <>
            <label className="sr-only" htmlFor={`percent-${row.task_id}`}>
              Avance de {row.name} en porcentaje
            </label>
            <input
              id={`percent-${row.task_id}`}
              type="number"
              min={0}
              max={100}
              step={1}
              className="narrow"
              value={percent}
              onChange={(event) => setPercent(event.target.value)}
              onBlur={() =>
                commit(percent, row.percent_complete, "percent_complete", setPercent, 100)
              }
            />
          </>
        ) : (
          `${row.percent_complete}%`
        )}
      </td>
      <td>{money.format(row.planned_value)}</td>
      <td>{money.format(row.earned_value)}</td>
      <td>
        {canEdit ? (
          <>
            <label className="sr-only" htmlFor={`actual-${row.task_id}`}>
              Costo real de {row.name}
            </label>
            <input
              id={`actual-${row.task_id}`}
              type="number"
              min={0}
              step="0.01"
              className="money"
              value={actual}
              onChange={(event) => setActual(event.target.value)}
              onBlur={() => commit(actual, row.actual_cost, "actual_cost", setActual, null)}
            />
          </>
        ) : (
          money.format(row.actual_cost)
        )}
      </td>
    </tr>
  );
}
