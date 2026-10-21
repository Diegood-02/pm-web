import { useCallback, useEffect, useState } from "react";

import { api } from "../api/endpoints";
import type {
  Assignment,
  Dependency,
  Member,
  Project,
  Resource,
  Schedule,
  Task,
} from "../api/types";

export interface ProjectData {
  project: Project;
  members: Member[];
  tasks: Task[];
  dependencies: Dependency[];
  schedule: Schedule;
  resources: Resource[];
  assignments: Assignment[];
}

/**
 * Carga todo lo necesario para la vista del proyecto y lo vuelve a cargar
 * cada `pollMs` mientras la pestaña esté visible. Así los cambios de otras
 * personas aparecen sin recargar la página.
 */
export function useProjectData(projectId: number, pollMs = 15000) {
  const [data, setData] = useState<ProjectData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [project, members, tasks, dependencies, schedule, resources, assignments] =
        await Promise.all([
          api.project(projectId),
          api.members(projectId),
          api.tasks(projectId),
          api.dependencies(projectId),
          api.schedule(projectId),
          api.resources(projectId),
          api.assignments(projectId),
        ]);
      setData({ project, members, tasks, dependencies, schedule, resources, assignments });
      setError(null);
    } catch {
      setError("No se pudo cargar el proyecto. Se reintentará automáticamente.");
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, pollMs);
    return () => clearInterval(timer);
  }, [refresh, pollMs]);

  return { data, error, refresh };
}
