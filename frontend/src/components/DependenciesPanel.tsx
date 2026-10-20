import { useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/endpoints";
import type { Dependency, DependencyType, Task } from "../api/types";

const DEPENDENCY_LABELS: Record<DependencyType, string> = {
  FS: "Fin a inicio",
  SS: "Inicio a inicio",
  FF: "Fin a fin",
  SF: "Inicio a fin",
};

interface DependenciesPanelProps {
  projectId: number;
  tasks: Task[];
  dependencies: Dependency[];
  canEdit: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
}

export function DependenciesPanel({
  projectId,
  tasks,
  dependencies,
  canEdit,
  onChanged,
  onError,
}: DependenciesPanelProps) {
  const [predecessor, setPredecessor] = useState("");
  const [successor, setSuccessor] = useState("");
  const [type, setType] = useState<DependencyType>("FS");
  const [lag, setLag] = useState("0");

  const wbsById = new Map(tasks.map((task) => [task.id, task.wbs]));

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await api.createDependency(projectId, {
        predecessor_id: Number(predecessor),
        successor_id: Number(successor),
        type,
        lag_days: Number(lag),
      });
      setPredecessor("");
      setSuccessor("");
      setType("FS");
      setLag("0");
      await onChanged();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "No se pudo crear la dependencia.");
    }
  }

  async function handleDelete(dependency: Dependency) {
    try {
      await api.deleteDependency(projectId, dependency.id);
      await onChanged();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "No se pudo borrar la dependencia.");
    }
  }

  return (
    <section aria-labelledby="titulo-dependencias">
      <h3 id="titulo-dependencias">Dependencias</h3>
      {dependencies.length === 0 ? (
        <p>No hay dependencias.</p>
      ) : (
        <table>
          <caption className="sr-only">Dependencias entre tareas</caption>
          <thead>
            <tr>
              <th scope="col">Predecesora</th>
              <th scope="col">Sucesora</th>
              <th scope="col">Tipo</th>
              <th scope="col">Retraso (días)</th>
              {canEdit && <th scope="col">Acción</th>}
            </tr>
          </thead>
          <tbody>
            {dependencies.map((dependency) => (
              <tr key={dependency.id}>
                <td>{wbsById.get(dependency.predecessor_id) ?? dependency.predecessor_id}</td>
                <td>{wbsById.get(dependency.successor_id) ?? dependency.successor_id}</td>
                <td>
                  {dependency.type} · {DEPENDENCY_LABELS[dependency.type]}
                </td>
                <td>{dependency.lag_days}</td>
                {canEdit && (
                  <td>
                    <button
                      type="button"
                      aria-label={`Eliminar dependencia ${wbsById.get(dependency.predecessor_id)} a ${wbsById.get(dependency.successor_id)}`}
                      onClick={() => void handleDelete(dependency)}
                    >
                      Eliminar
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {canEdit && tasks.length >= 2 && (
        <form className="inline-form" onSubmit={handleCreate} aria-label="Nueva dependencia">
          <h4>Nueva dependencia</h4>
          <div className="field">
            <label htmlFor="dep-pred">Predecesora</label>
            <select
              id="dep-pred"
              required
              value={predecessor}
              onChange={(e) => setPredecessor(e.target.value)}
            >
              <option value="">Elige una tarea</option>
              {tasks.map((task) => (
                <option key={task.id} value={task.id}>
                  {task.wbs} {task.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="dep-succ">Sucesora</label>
            <select
              id="dep-succ"
              required
              value={successor}
              onChange={(e) => setSuccessor(e.target.value)}
            >
              <option value="">Elige una tarea</option>
              {tasks.map((task) => (
                <option key={task.id} value={task.id}>
                  {task.wbs} {task.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="dep-type">Tipo</label>
            <select
              id="dep-type"
              value={type}
              onChange={(e) => setType(e.target.value as DependencyType)}
            >
              {(Object.keys(DEPENDENCY_LABELS) as DependencyType[]).map((option) => (
                <option key={option} value={option}>
                  {option} · {DEPENDENCY_LABELS[option]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="dep-lag">Retraso en días (negativo = adelanto)</label>
            <input
              id="dep-lag"
              type="number"
              step={1}
              className="narrow"
              value={lag}
              onChange={(e) => setLag(e.target.value)}
            />
          </div>
          <button type="submit">Agregar dependencia</button>
        </form>
      )}
    </section>
  );
}
