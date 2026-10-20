import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CostReport } from "../../src/api/types";
import { CostsPanel } from "../../src/components/CostsPanel";
import { installApi } from "../support/api";
import { tasks } from "../fixtures";

// Mismo escenario de referencia que tests/costing (backend): SPI 0.8333 dispara la alerta.
const report: CostReport = {
  project_id: 5,
  status_date: "2026-01-07",
  summary: {
    bac: 4900,
    pv: 2700,
    ev: 2250,
    ac: 2400,
    cv: -150,
    sv: -450,
    cpi: 0.9375,
    spi: 0.8333,
    threshold: 0.9,
    cpi_alert: false,
    spi_alert: true,
  },
  tasks: [
    {
      task_id: 10,
      wbs: "1",
      name: "Diseño",
      budget: 4500,
      percent_complete: 50,
      fixed_cost: 500,
      planned_value: 2700,
      earned_value: 2250,
      actual_cost: 2400,
    },
    {
      task_id: 11,
      wbs: "2",
      name: "Construcción",
      budget: 400,
      percent_complete: 0,
      fixed_cost: 0,
      planned_value: 0,
      earned_value: 0,
      actual_cost: 0,
    },
  ],
};

function renderPanel(
  canEdit: boolean,
  onAction = vi.fn(async (action: () => Promise<unknown>) => {
    await action();
  }),
) {
  render(
    <CostsPanel
      projectId={5}
      tasks={tasks}
      canEdit={canEdit}
      stamp="inicial"
      onAction={onAction}
    />,
  );
  return onAction;
}

describe("CostsPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("muestra los indicadores y alerta cuando SPI está por debajo de 0.9", async () => {
    installApi({ "GET /projects/5/costs": { body: report } });
    renderPanel(false);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("SPI 0.8333 está por debajo de 0.9");
    expect(alert).not.toHaveTextContent("CPI");
    expect(screen.getByText("0.9375")).toBeInTheDocument();
  });

  it("sin alerta cuando CPI y SPI están sobre el umbral", async () => {
    const healthy: CostReport = {
      ...report,
      summary: { ...report.summary, spi: 1.0, spi_alert: false, cpi: 1.1, cpi_alert: false },
    };
    installApi({ "GET /projects/5/costs": { body: healthy } });
    renderPanel(false);

    await screen.findByText("Presupuesto (BAC)");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("guarda el avance con la versión actual de la tarea", async () => {
    const fetchMock = installApi({
      "GET /projects/5/costs": { body: report },
      "PATCH /projects/5/tasks/10": { body: { ...tasks[0], percent_complete: 60, version: 3 } },
    });
    const onAction = renderPanel(true);

    const input = await screen.findByLabelText("Avance de Diseño en porcentaje");
    fireEvent.change(input, { target: { value: "60" } });
    fireEvent.blur(input);

    await waitFor(() => expect(onAction).toHaveBeenCalled());
    const patch = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(String(patch?.[1]?.body))).toEqual({
      version: tasks[0].version,
      percent_complete: 60,
    });
  });

  it("rechaza un avance fuera de 0 a 100 sin llamar a la API", async () => {
    const fetchMock = installApi({ "GET /projects/5/costs": { body: report } });
    const onAction = renderPanel(true);

    const input = await screen.findByLabelText("Avance de Diseño en porcentaje");
    fireEvent.change(input, { target: { value: "150" } });
    fireEvent.blur(input);

    expect(onAction).not.toHaveBeenCalled();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(false);
    expect((input as HTMLInputElement).value).toBe("50");
  });

  it("un lector ve los montos sin campos editables", async () => {
    installApi({ "GET /projects/5/costs": { body: report } });
    renderPanel(false);

    await screen.findByText("Presupuesto (BAC)");
    expect(screen.queryByLabelText("Avance de Diseño en porcentaje")).not.toBeInTheDocument();
  });
});
