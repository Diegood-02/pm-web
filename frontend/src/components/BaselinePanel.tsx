import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import type { BaselineSummary, BaselineVariance } from "../api/types";

interface BaselinePanelProps {
  projectId: number;
  canManage: boolean;
}

function formatVariance(days: number | null): string {
  if (days === null) return "—";
  if (days === 0) return "0";
  return days > 0 ? `+${days}` : String(days);
}

export function BaselinePanel({ projectId, canManage }: BaselinePanelProps) {
  const [baselines, setBaselines] = useState<BaselineSummary[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [comparison, setComparison] = useState<BaselineVariance[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .baselines(projectId)
      .then((list) => {
        setBaselines(list);
        setSelectedId((current) => current ?? list.at(-1)?.id ?? null);
      })
      .catch(() => setError("No se pudieron cargar las líneas base."));
  }, [projectId]);

  useEffect(() => {
    if (selectedId === null) {
      setComparison(null);
      return;
    }
    api
      .baselineComparison(projectId, selectedId)
      .then(setComparison)
      .catch(() => setError("No se pudo cargar la comparación."));
  }, [projectId, selectedId]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const created = await api.createBaseline(projectId, name.trim());
      setBaselines((current) => [...(current ?? []), created]);
      setSelectedId(created.id);
      setName("");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo guardar la línea base.");
    }
  }

  return (
    <section aria-labelledby="titulo-linea-base">
      <h2 id="titulo-linea-base">Línea base</h2>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      {baselines?.length === 0 && <p>Todavía no hay líneas base guardadas.</p>}
      {baselines && baselines.length > 0 && (
        <div className="field">
          <label htmlFor="baseline-select">Línea base a comparar</label>
          <select
            id="baseline-select"
            value={selectedId ?? ""}
            onChange={(event) => setSelectedId(Number(event.target.value))}
          >
            {baselines.map((baseline) => (
              <option key={baseline.id} value={baseline.id}>
                {baseline.name} · fin {baseline.project_finish}
              </option>
            ))}
          </select>
        </div>
      )}

      {comparison && (
        <table>
          <caption className="sr-only">Comparación de la línea base con el plan actual</caption>
          <thead>
            <tr>
              <th scope="col">WBS</th>
              <th scope="col">Tarea</th>
              <th scope="col">Inicio línea base</th>
              <th scope="col">Inicio actual</th>
              <th scope="col">Variación inicio (días)</th>
              <th scope="col">Fin línea base</th>
              <th scope="col">Fin actual</th>
              <th scope="col">Variación fin (días)</th>
            </tr>
          </thead>
          <tbody>
            {comparison.map((row) => (
              <tr
                key={`${row.task_id ?? "eliminada"}-${row.wbs}`}
                className={
                  row.finish_variance_days && row.finish_variance_days > 0 ? "late-row" : undefined
                }
              >
                <td>{row.wbs}</td>
                <td>{row.task_id === null ? `${row.name} (eliminada)` : row.name}</td>
                <td>{row.baseline_start}</td>
                <td>{row.current_start ?? "—"}</td>
                <td>{formatVariance(row.start_variance_days)}</td>
                <td>{row.baseline_finish}</td>
                <td>{row.current_finish ?? "—"}</td>
                <td>{formatVariance(row.finish_variance_days)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {canManage && (
        <form className="inline-form" onSubmit={handleCreate} aria-label="Guardar línea base">
          <h3>Guardar línea base del plan actual</h3>
          <div className="field">
            <label htmlFor="baseline-name">Nombre</label>
            <input
              id="baseline-name"
              required
              maxLength={200}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <button type="submit">Guardar línea base</button>
        </form>
      )}
    </section>
  );
}
