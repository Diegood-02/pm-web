import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import type { Assignment, Resource, Task } from "../api/types";

interface ResourcesPanelProps {
  projectId: number;
  tasks: Task[];
  resources: Resource[];
  assignments: Assignment[];
  canEdit: boolean;
  onChanged: () => Promise<void>;
}

function errorMessage(caught: unknown, fallback: string): string {
  return caught instanceof ApiError ? caught.message : fallback;
}

export function ResourcesPanel({
  projectId,
  tasks,
  resources,
  assignments,
  canEdit,
  onChanged,
}: ResourcesPanelProps) {
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newMaxUnits, setNewMaxUnits] = useState("100");
  const [newRate, setNewRate] = useState("0");
  const [taskId, setTaskId] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [units, setUnits] = useState("100");

  const taskNames = new Map(tasks.map((task) => [task.id, `${task.wbs} ${task.name}`]));
  const resourceNames = new Map(resources.map((resource) => [resource.id, resource.name]));

  async function run(action: () => Promise<unknown>, fallback: string) {
    setError(null);
    try {
      await action();
      await onChanged();
    } catch (caught) {
      setError(errorMessage(caught, fallback));
    }
  }

  async function handleCreateResource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await run(async () => {
      await api.createResource(projectId, {
        name: newName.trim(),
        max_units: Number(newMaxUnits),
        hourly_rate: Number(newRate),
      });
      setNewName("");
      setNewMaxUnits("100");
      setNewRate("0");
    }, "No se pudo crear el recurso.");
  }

  async function handleAssign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await run(async () => {
      await api.assignResource(projectId, Number(taskId), {
        resource_id: Number(resourceId),
        units_percent: Number(units),
      });
    }, "No se pudo asignar el recurso. Puede que ya esté asignado a esa tarea.");
  }

  return (
    <section aria-labelledby="titulo-recursos">
      <h2 id="titulo-recursos">Recursos</h2>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      <table>
        <caption className="sr-only">Recursos del proyecto</caption>
        <thead>
          <tr>
            <th scope="col">Nombre</th>
            <th scope="col">Capacidad máxima (%)</th>
            <th scope="col">Tarifa por hora</th>
            {canEdit && <th scope="col">Acción</th>}
          </tr>
        </thead>
        <tbody>
          {resources.map((resource) => (
            <tr key={resource.id}>
              <td>{resource.name}</td>
              <td>{resource.max_units}</td>
              <td>
                {canEdit ? (
                  <RateInput
                    resource={resource}
                    onSave={(rate) =>
                      run(
                        () => api.updateResource(projectId, resource.id, { hourly_rate: rate }),
                        "No se pudo guardar la tarifa.",
                      )
                    }
                  />
                ) : (
                  resource.hourly_rate
                )}
              </td>
              {canEdit && (
                <td>
                  <button
                    type="button"
                    aria-label={`Eliminar recurso ${resource.name}`}
                    onClick={() =>
                      void run(
                        () => api.deleteResource(projectId, resource.id),
                        "No se pudo eliminar el recurso.",
                      )
                    }
                  >
                    Eliminar
                  </button>
                </td>
              )}
            </tr>
          ))}
          {resources.length === 0 && (
            <tr>
              <td colSpan={canEdit ? 4 : 3}>No hay recursos todavía.</td>
            </tr>
          )}
        </tbody>
      </table>

      <h3>Asignaciones</h3>
      <table>
        <caption className="sr-only">Asignaciones de recursos a tareas</caption>
        <thead>
          <tr>
            <th scope="col">Tarea</th>
            <th scope="col">Recurso</th>
            <th scope="col">Dedicación (%)</th>
            {canEdit && <th scope="col">Acción</th>}
          </tr>
        </thead>
        <tbody>
          {assignments.map((assignment) => (
            <tr key={assignment.id}>
              <td>{taskNames.get(assignment.task_id) ?? assignment.task_id}</td>
              <td>{resourceNames.get(assignment.resource_id) ?? assignment.resource_id}</td>
              <td>{assignment.units_percent}</td>
              {canEdit && (
                <td>
                  <button
                    type="button"
                    aria-label={`Quitar asignación ${assignment.id}`}
                    onClick={() =>
                      void run(
                        () => api.deleteAssignment(projectId, assignment.id),
                        "No se pudo quitar la asignación.",
                      )
                    }
                  >
                    Quitar
                  </button>
                </td>
              )}
            </tr>
          ))}
          {assignments.length === 0 && (
            <tr>
              <td colSpan={canEdit ? 4 : 3}>No hay asignaciones todavía.</td>
            </tr>
          )}
        </tbody>
      </table>

      {canEdit && (
        <div className="forms">
          <form className="inline-form" onSubmit={handleCreateResource} aria-label="Nuevo recurso">
            <h3>Nuevo recurso</h3>
            <div className="field">
              <label htmlFor="resource-name">Nombre</label>
              <input
                id="resource-name"
                required
                maxLength={200}
                value={newName}
                onChange={(event) => setNewName(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="resource-max">Capacidad máxima (%)</label>
              <input
                id="resource-max"
                type="number"
                min={1}
                max={1000}
                className="narrow"
                value={newMaxUnits}
                onChange={(event) => setNewMaxUnits(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="resource-rate">Tarifa por hora</label>
              <input
                id="resource-rate"
                type="number"
                min={0}
                step="0.01"
                className="narrow"
                value={newRate}
                onChange={(event) => setNewRate(event.target.value)}
              />
            </div>
            <button type="submit">Agregar recurso</button>
          </form>

          <form className="inline-form" onSubmit={handleAssign} aria-label="Asignar recurso">
            <h3>Asignar a tarea</h3>
            <div className="field">
              <label htmlFor="assign-task">Tarea</label>
              <select
                id="assign-task"
                required
                value={taskId}
                onChange={(event) => setTaskId(event.target.value)}
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
              <label htmlFor="assign-resource">Recurso</label>
              <select
                id="assign-resource"
                required
                value={resourceId}
                onChange={(event) => setResourceId(event.target.value)}
              >
                <option value="">Elige un recurso</option>
                {resources.map((resource) => (
                  <option key={resource.id} value={resource.id}>
                    {resource.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="assign-units">Dedicación (%)</label>
              <input
                id="assign-units"
                type="number"
                min={1}
                max={1000}
                className="narrow"
                value={units}
                onChange={(event) => setUnits(event.target.value)}
              />
            </div>
            <button type="submit">Asignar</button>
          </form>
        </div>
      )}
    </section>
  );
}

function RateInput({
  resource,
  onSave,
}: {
  resource: Resource;
  onSave: (rate: number) => Promise<void>;
}) {
  const [draft, setDraft] = useState(String(resource.hourly_rate));

  function commit() {
    const value = Number(draft);
    if (draft.trim() === "" || !Number.isFinite(value) || value < 0) {
      setDraft(String(resource.hourly_rate));
      return;
    }
    if (value !== resource.hourly_rate) void onSave(value);
  }

  return (
    <>
      <label className="sr-only" htmlFor={`rate-${resource.id}`}>
        Tarifa por hora de {resource.name}
      </label>
      <input
        id={`rate-${resource.id}`}
        type="number"
        min={0}
        step="0.01"
        className="narrow"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
      />
    </>
  );
}
