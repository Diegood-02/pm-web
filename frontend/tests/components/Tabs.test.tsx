import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { TabList } from "../../src/components/Tabs";

const TABS = [
  { id: "tareas", label: "Tareas" },
  { id: "gantt", label: "Gantt" },
  { id: "recursos", label: "Recursos" },
];

function Harness({ onChange }: { onChange: (id: string) => void }) {
  const [selected, setSelected] = useState("tareas");
  return (
    <TabList
      tabs={TABS}
      selected={selected}
      onSelect={(id) => {
        setSelected(id);
        onChange(id);
      }}
    />
  );
}

describe("TabList", () => {
  it("se mueve con flechas y con Inicio/Fin", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    const first = screen.getByRole("tab", { name: "Tareas" });

    expect(first).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(first, { key: "ArrowRight" });
    expect(onChange).toHaveBeenLastCalledWith("gantt");
    fireEvent.keyDown(screen.getByRole("tab", { name: "Gantt" }), { key: "End" });
    expect(onChange).toHaveBeenLastCalledWith("recursos");
    fireEvent.keyDown(screen.getByRole("tab", { name: "Recursos" }), { key: "Home" });
    expect(onChange).toHaveBeenLastCalledWith("tareas");
  });

  it("la flecha izquierda desde la primera pestaña va a la última", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);

    fireEvent.keyDown(screen.getByRole("tab", { name: "Tareas" }), { key: "ArrowLeft" });

    expect(onChange).toHaveBeenLastCalledWith("recursos");
  });

  it("solo la pestaña seleccionada entra en el orden de tabulación", () => {
    render(<Harness onChange={() => undefined} />);

    expect(screen.getByRole("tab", { name: "Tareas" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: "Gantt" })).toHaveAttribute("tabindex", "-1");
  });
});
