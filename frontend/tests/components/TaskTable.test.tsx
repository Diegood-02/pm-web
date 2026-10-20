import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Task } from "../../src/api/types";
import { TaskTable } from "../../src/components/TaskTable";
import { schedule, tasks } from "../fixtures";

function renderTable(
  overrides: Partial<Parameters<typeof TaskTable>[0]> = {},
  list: Task[] = tasks,
) {
  const handlers = {
    onUpdate: vi.fn().mockResolvedValue(undefined),
    onMove: vi.fn().mockResolvedValue(undefined),
    onCreate: vi.fn().mockResolvedValue(undefined),
    onDelete: vi.fn().mockResolvedValue(undefined),
  };
  render(<TaskTable tasks={list} schedule={schedule} canEdit {...handlers} {...overrides} />);
  return handlers;
}

describe("TaskTable", () => {
  it("muestra el WBS, las fechas y la marca de ruta crítica", () => {
    renderTable();

    expect(screen.getByText("2026-01-08")).toBeInTheDocument();
    expect(screen.getAllByText("Sí")).not.toHaveLength(0);
  });

  it("guarda el nombre con la versión actual al salir del campo", () => {
    const handlers = renderTable();

    const input = screen.getByLabelText("Nombre de la tarea 1");
    fireEvent.change(input, { target: { value: "Diseño detallado" } });
    fireEvent.blur(input);

    expect(handlers.onUpdate).toHaveBeenCalledWith(tasks[0], { name: "Diseño detallado" });
  });

  it("no guarda si el nombre no cambió", () => {
    const handlers = renderTable();

    fireEvent.blur(screen.getByLabelText("Nombre de la tarea 1"));

    expect(handlers.onUpdate).not.toHaveBeenCalled();
  });

  it("baja una tarea a su siguiente posición entre hermanas", () => {
    const handlers = renderTable();

    fireEvent.click(screen.getByRole("button", { name: "Bajar Diseño" }));

    expect(handlers.onMove).toHaveBeenCalledWith(tasks[0], null, 1);
  });

  it("subir la primera tarea de un nivel está deshabilitado", () => {
    renderTable();

    expect(screen.getByRole("button", { name: "Subir Diseño" })).toBeDisabled();
  });

  it("marcar hito envía duración 0", () => {
    const handlers = renderTable();

    fireEvent.click(screen.getByLabelText("Diseño es hito"));

    expect(handlers.onUpdate).toHaveBeenCalledWith(tasks[0], {
      is_milestone: true,
      duration_days: 0,
    });
  });

  it("sin permiso de edición no muestra acciones", () => {
    renderTable({ canEdit: false });

    expect(screen.queryByRole("button", { name: /Eliminar/ })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Nombre de la tarea 1")).not.toBeInTheDocument();
    expect(screen.getByText("Diseño")).toBeInTheDocument();
  });

  it("eliminar pide confirmación", () => {
    const handlers = renderTable();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar Diseño" }));

    expect(confirm).toHaveBeenCalled();
    expect(handlers.onDelete).not.toHaveBeenCalled();
    confirm.mockRestore();
  });
});
