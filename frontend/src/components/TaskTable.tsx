import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import type { Schedule, ScheduleTask, Task } from "../api/types";

export interface TaskPatch {
  name?: string;
  duration_days?: number;
  is_milestone?: boolean;
}

export interface NewTask {
  name: string;
  duration_days: number;
  is_milestone: boolean;
  parent_id: number | null;
}

interface TaskTableProps {
  tasks: Task[];
  schedule: Schedule;
  canEdit: boolean;
  onUpdate: (task: Task, patch: TaskPatch) => Promise<void>;
  onMove: (task: Task, parentId: number | null, position: number) => Promise<void>;
  onCreate: (input: NewTask) => Promise<void>;
  onDelete: (task: Task) => Promise<void>;
}

function siblingsOf(tasks: Task[], parentId: number | null): Task[] {
  return tasks
    .filter((task) => task.parent_id === parentId)
    .sort((a, b) => a.position - b.position);
}

export function TaskTable({
  tasks,
  schedule,
  canEdit,
  onUpdate,
  onMove,
  onCreate,
  onDelete,
}: TaskTableProps) {
  const scheduleById = useMemo(
    () => new Map<number, ScheduleTask>(schedule.tasks.map((entry) => [entry.task_id, entry])),
    [schedule],
  );

  return (
    <div className="task-table-wrapper">
      <table className="task-table">
        <caption className="sr-only">Tareas del proyecto en estructura WBS</caption>
        <thead>
          <tr>
            <th scope="col">WBS</th>
            <th scope="col">Nombre</th>
            <th scope="col">Duración (días)</th>
            <th scope="col">Hito</th>
            <th scope="col">Inicio</th>
            <th scope="col">Fin</th>
            <th scope="col">Crítica</th>
            {canEdit && <th scope="col">Acciones</th>}
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <TaskRow
              key={`${task.id}-${task.version}`}
              task={task}
              tasks={tasks}
              entry={scheduleById.get(task.id)}
              canEdit={canEdit}
              onUpdate={onUpdate}
              onMove={onMove}
              onDelete={onDelete}
            />
          ))}
          {tasks.length === 0 && (
            <tr>
              <td colSpan={canEdit ? 8 : 7}>Todavía no hay tareas.</td>
            </tr>
          )}
        </tbody>
      </table>

      {canEdit && <NewTaskForm tasks={tasks} onCreate={onCreate} />}
    </div>
  );
}

interface TaskRowProps {
  task: Task;
  tasks: Task[];
  entry: ScheduleTask | undefined;
  canEdit: boolean;
  onUpdate: TaskTableProps["onUpdate"];
  onMove: TaskTableProps["onMove"];
  onDelete: TaskTableProps["onDelete"];
}

function TaskRow({ task, tasks, entry, canEdit, onUpdate, onMove, onDelete }: TaskRowProps) {
  const [name, setName] = useState(task.name);
  const [duration, setDuration] = useState(String(task.duration_days));
  const depth = task.wbs.split(".").length - 1;

  const siblings = siblingsOf(tasks, task.parent_id);
  const index = siblings.findIndex((sibling) => sibling.id === task.id);
  const previous = index > 0 ? siblings[index - 1] : undefined;
  const parent = tasks.find((candidate) => candidate.id === task.parent_id);

  async function commitName() {
    const trimmed = name.trim();
    if (!trimmed) {
      setName(task.name);
      return;
    }
    if (trimmed !== task.name) await onUpdate(task, { name: trimmed });
  }

  async function commitDuration() {
    const value = Number(duration);
    if (!Number.isInteger(value) || value < 0) {
      setDuration(String(task.duration_days));
      return;
    }
    if (value !== task.duration_days) await onUpdate(task, { duration_days: value });
  }

  function toggleMilestone(checked: boolean) {
    void onUpdate(
      task,
      checked ? { is_milestone: true, duration_days: 0 } : { is_milestone: false },
    );
  }

  return (
    <tr className={entry?.is_critical ? "critical-row" : undefined}>
      <th scope="row" className="wbs">
        <span style={{ paddingLeft: `${depth * 1.25}rem` }}>{task.wbs}</span>
      </th>
      <td>
        {canEdit ? (
          <>
            <label className="sr-only" htmlFor={`task-name-${task.id}`}>
              Nombre de la tarea {task.wbs}
            </label>
            <input
              id={`task-name-${task.id}`}
              value={name}
              maxLength={200}
              onChange={(event) => setName(event.target.value)}
              onBlur={() => void commitName()}
              onKeyDown={(event) => {
                if (event.key === "Enter") event.currentTarget.blur();
              }}
            />
          </>
        ) : (
          task.name
        )}
      </td>
      <td>
        {canEdit && !task.is_milestone ? (
          <>
            <label className="sr-only" htmlFor={`task-duration-${task.id}`}>
              Duración de {task.name}
            </label>
            <input
              id={`task-duration-${task.id}`}
              type="number"
              min={0}
              step={1}
              className="narrow"
              value={duration}
              onChange={(event) => setDuration(event.target.value)}
              onBlur={() => void commitDuration()}
            />
          </>
        ) : (
          task.duration_days
        )}
      </td>
      <td>
        {canEdit ? (
          <>
            <label className="sr-only" htmlFor={`task-milestone-${task.id}`}>
              {task.name} es hito
            </label>
            <input
              id={`task-milestone-${task.id}`}
              type="checkbox"
              checked={task.is_milestone}
              onChange={(event) => toggleMilestone(event.target.checked)}
            />
          </>
        ) : task.is_milestone ? (
          "Sí"
        ) : (
          "No"
        )}
      </td>
      <td>{entry?.start_date}</td>
      <td>{entry?.finish_date}</td>
      <td>{entry?.is_critical ? "Sí" : "No"}</td>
      {canEdit && (
        <td className="actions">
          <button
            type="button"
            aria-label={`Subir ${task.name}`}
            disabled={index <= 0}
            onClick={() => onMove(task, task.parent_id, index - 1)}
          >
            ↑
          </button>
          <button
            type="button"
            aria-label={`Bajar ${task.name}`}
            disabled={index < 0 || index >= siblings.length - 1}
            onClick={() => onMove(task, task.parent_id, index + 1)}
          >
            ↓
          </button>
          <button
            type="button"
            aria-label={`Aumentar sangría de ${task.name}`}
            disabled={!previous}
            onClick={() =>
              previous && onMove(task, previous.id, siblingsOf(tasks, previous.id).length)
            }
          >
            →
          </button>
          <button
            type="button"
            aria-label={`Quitar sangría de ${task.name}`}
            disabled={!parent}
            onClick={() => parent && onMove(task, parent.parent_id, parent.position + 1)}
          >
            ←
          </button>
          <button
            type="button"
            aria-label={`Eliminar ${task.name}`}
            onClick={() => {
              if (window.confirm(`¿Eliminar "${task.name}" y sus subtareas?`)) {
                void onDelete(task);
              }
            }}
          >
            Eliminar
          </button>
        </td>
      )}
    </tr>
  );
}

function NewTaskForm({
  tasks,
  onCreate,
}: {
  tasks: Task[];
  onCreate: (input: NewTask) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [duration, setDuration] = useState("1");
  const [milestone, setMilestone] = useState(false);
  const [parentId, setParentId] = useState<string>("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onCreate({
      name: name.trim(),
      duration_days: milestone ? 0 : Number(duration),
      is_milestone: milestone,
      parent_id: parentId === "" ? null : Number(parentId),
    });
    setName("");
    setDuration("1");
    setMilestone(false);
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit} aria-label="Nueva tarea">
      <h3>Nueva tarea</h3>
      <div className="field">
        <label htmlFor="new-task-name">Nombre</label>
        <input
          id="new-task-name"
          required
          maxLength={200}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="new-task-duration">Duración (días)</label>
        <input
          id="new-task-duration"
          type="number"
          min={0}
          className="narrow"
          disabled={milestone}
          value={milestone ? "0" : duration}
          onChange={(event) => setDuration(event.target.value)}
        />
      </div>
      <div className="field checkbox">
        <input
          id="new-task-milestone"
          type="checkbox"
          checked={milestone}
          onChange={(event) => setMilestone(event.target.checked)}
        />
        <label htmlFor="new-task-milestone">Es hito</label>
      </div>
      <div className="field">
        <label htmlFor="new-task-parent">Dentro de</label>
        <select
          id="new-task-parent"
          value={parentId}
          onChange={(event) => setParentId(event.target.value)}
        >
          <option value="">Nivel superior</option>
          {tasks.map((task) => (
            <option key={task.id} value={task.id}>
              {task.wbs} {task.name}
            </option>
          ))}
        </select>
      </div>
      <button type="submit">Agregar tarea</button>
    </form>
  );
}
