import { useState } from "react";
import { useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { BaselinePanel } from "../components/BaselinePanel";
import { CostsPanel } from "../components/CostsPanel";
import { DependenciesPanel } from "../components/DependenciesPanel";
import { GanttView } from "../components/GanttView";
import { ResourcesPanel } from "../components/ResourcesPanel";
import { TabList } from "../components/Tabs";
import type { TabDefinition } from "../components/Tabs";
import { TaskTable } from "../components/TaskTable";
import type { NewTask, TaskPatch } from "../components/TaskTable";
import { useProjectData } from "../hooks/useProjectData";
import type { Task } from "../api/types";

const TABS: TabDefinition[] = [
  { id: "tareas", label: "Tareas" },
  { id: "gantt", label: "Gantt" },
  { id: "recursos", label: "Recursos" },
  { id: "costos", label: "Costos" },
  { id: "linea-base", label: "Línea base" },
];

const CONFLICT_MESSAGE =
  "Otra persona cambió esta información. Se recargó con los datos más recientes; revisa y vuelve a intentarlo.";

export function ProjectPage() {
  const { projectId: rawId } = useParams();
  const projectId = Number(rawId);
  const { user } = useAuth();
  const [selectedTab, setSelectedTab] = useState("tareas");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data, error: loadError, refresh } = useProjectData(projectId);

  if (!Number.isInteger(projectId) || projectId <= 0) {
    return <p role="alert">Proyecto no válido.</p>;
  }
  if (!data && !loadError) return <p role="status">Cargando proyecto…</p>;
  if (!data) return <p role="alert">{loadError}</p>;

  // Un admin global actúa como project manager en cualquier proyecto.
  const role =
    user?.role === "admin"
      ? "project_manager"
      : data.members.find((member) => member.user_id === user?.id)?.role;
  if (!role) {
    return <p role="alert">No tienes acceso a este proyecto.</p>;
  }
  const canEdit = role === "project_manager" || role === "miembro";
  const canManage = role === "project_manager";

  /** Ejecuta una acción y refresca. Un 409 significa que alguien más cambió el dato primero. */
  async function run(action: () => Promise<unknown>, fallback: string) {
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice("Cambios guardados.");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        setError(CONFLICT_MESSAGE);
      } else {
        setError(caught instanceof ApiError ? caught.message : fallback);
      }
    } finally {
      await refresh();
    }
  }

  const { project, tasks, schedule, dependencies, resources, assignments } = data;

  return (
    <article aria-labelledby="titulo-proyecto">
      <header className="project-header">
        <h1 id="titulo-proyecto">{project.name}</h1>
        <p className="summary">
          Duración: {schedule.duration_days} días laborables · Fin previsto:{" "}
          {schedule.project_finish}· Ruta crítica: {schedule.critical_path.length} tareas · Tu rol:{" "}
          {role}
        </p>
      </header>

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {loadError && (
        <p role="alert" className="error">
          {loadError}
        </p>
      )}
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}

      <TabList tabs={TABS} selected={selectedTab} onSelect={setSelectedTab} />

      <div
        role="tabpanel"
        id={`panel-${selectedTab}`}
        aria-labelledby={`tab-${selectedTab}`}
        tabIndex={0}
        className="tabpanel"
      >
        {selectedTab === "tareas" && (
          <TaskTable
            tasks={tasks}
            schedule={schedule}
            canEdit={canEdit}
            onUpdate={(task: Task, patch: TaskPatch) =>
              run(
                () => api.updateTask(projectId, task.id, { version: task.version, ...patch }),
                "No se pudo guardar la tarea.",
              )
            }
            onMove={(task: Task, parentId: number | null, position: number) =>
              run(
                () =>
                  api.moveTask(projectId, task.id, {
                    version: task.version,
                    parent_id: parentId,
                    position,
                  }),
                "No se pudo mover la tarea.",
              )
            }
            onCreate={(input: NewTask) =>
              run(() => api.createTask(projectId, input), "No se pudo crear la tarea.")
            }
            onDelete={(task: Task) =>
              run(() => api.deleteTask(projectId, task.id), "No se pudo borrar la tarea.")
            }
          />
        )}

        {selectedTab === "gantt" && (
          <>
            <GanttView schedule={schedule} dependencies={dependencies} />
            <DependenciesPanel
              projectId={projectId}
              tasks={tasks}
              dependencies={dependencies}
              canEdit={canEdit}
              onChanged={refresh}
              onError={setError}
            />
          </>
        )}

        {selectedTab === "recursos" && (
          <ResourcesPanel
            projectId={projectId}
            tasks={tasks}
            resources={resources}
            assignments={assignments}
            canEdit={canEdit}
            onChanged={refresh}
          />
        )}

        {selectedTab === "costos" && (
          <CostsPanel
            projectId={projectId}
            tasks={tasks}
            canEdit={canEdit}
            stamp={data}
            onAction={run}
          />
        )}

        {selectedTab === "linea-base" && (
          <>
            <BaselinePanel projectId={projectId} canManage={canManage} />
          </>
        )}
      </div>
    </article>
  );
}
