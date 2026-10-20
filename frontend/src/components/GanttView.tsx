import { useEffect, useMemo, useRef } from "react";
import Gantt from "frappe-gantt";
import type { GanttTask } from "frappe-gantt";
// El campo "exports" de frappe-gantt no expone su CSS como subruta, así que se importa por ruta.
import "../../node_modules/frappe-gantt/dist/frappe-gantt.css";

import type { Dependency, Schedule } from "../api/types";

/** Convierte el cronograma en tareas para frappe-gantt. Las tareas críticas llevan la clase `critical`. */
export function buildGanttTasks(schedule: Schedule, dependencies: Dependency[]): GanttTask[] {
  return schedule.tasks.map((entry) => {
    const predecessors = dependencies
      .filter((dependency) => dependency.successor_id === entry.task_id)
      .map((dependency) => `task-${dependency.predecessor_id}`);
    return {
      id: `task-${entry.task_id}`,
      name: `${entry.wbs} ${entry.name}`,
      start: entry.start_date,
      end: entry.finish_date,
      progress: 0,
      dependencies: predecessors.join(","),
      custom_class: entry.is_critical ? "critical" : "",
    };
  });
}

interface GanttViewProps {
  schedule: Schedule;
  dependencies: Dependency[];
}

export function GanttView({ schedule, dependencies }: GanttViewProps) {
  const container = useRef<HTMLDivElement>(null);
  const ganttTasks = useMemo(
    () => buildGanttTasks(schedule, dependencies),
    [schedule, dependencies],
  );

  useEffect(() => {
    const element = container.current;
    if (!element || ganttTasks.length === 0) return;
    element.innerHTML = "";
    new Gantt(element, ganttTasks, { view_mode: "Week", bar_height: 22 });
    return () => {
      element.innerHTML = "";
    };
  }, [ganttTasks]);

  return (
    <div className="gantt">
      <p className="muted">
        Ruta crítica en rojo. El diagrama dibuja todas las dependencias como fin a inicio; el tipo
        exacto de cada una aparece en la tabla de dependencias.
      </p>
      {ganttTasks.length === 0 ? (
        <p>No hay tareas para mostrar.</p>
      ) : (
        <div
          ref={container}
          className="gantt-canvas"
          role="img"
          aria-label={`Diagrama de Gantt con ${ganttTasks.length} tareas. Ruta crítica: ${schedule.critical_path.length} tareas.`}
        />
      )}
    </div>
  );
}
