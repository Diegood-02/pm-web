import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildGanttTasks, GanttView } from "../../src/components/GanttView";
import { schedule } from "../fixtures";

const gantt = vi.hoisted(() => ({ calls: [] as unknown[][] }));

vi.mock("frappe-gantt", () => {
  class MockGantt {
    constructor(element: HTMLElement, tasks: unknown[], options: unknown) {
      gantt.calls.push([element, tasks, options]);
    }
  }
  return { default: MockGantt };
});

const dependencies = [
  { id: 1, predecessor_id: 10, successor_id: 11, type: "FS" as const, lag_days: 0 },
];

describe("buildGanttTasks", () => {
  it("marca las tareas críticas y une dependencias por id", () => {
    const tasks = buildGanttTasks(schedule, dependencies);

    expect(tasks[0]).toEqual({
      id: "task-10",
      name: "1 Diseño",
      start: "2026-01-05",
      end: "2026-01-07",
      progress: 0,
      dependencies: "",
      custom_class: "critical",
    });
    expect(tasks[1].dependencies).toBe("task-10");
  });
});

describe("GanttView", () => {
  beforeEach(() => {
    gantt.calls.length = 0;
  });

  it("entrega las tareas al componente de Gantt y muestra el resumen accesible", () => {
    render(<GanttView schedule={schedule} dependencies={dependencies} />);

    expect(gantt.calls).toHaveLength(1);
    expect(gantt.calls[0][1]).toHaveLength(2);
    expect(screen.getByRole("img", { name: /Ruta crítica: 2 tareas/ })).toBeInTheDocument();
  });

  it("indica cuando no hay tareas", () => {
    render(<GanttView schedule={{ ...schedule, tasks: [] }} dependencies={[]} />);

    expect(screen.getByText("No hay tareas para mostrar.")).toBeInTheDocument();
    expect(gantt.calls).toHaveLength(0);
  });
});
