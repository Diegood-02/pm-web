import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../../src/App";
import { AuthProvider } from "../../src/auth/AuthContext";
import { installApi } from "../support/api";
import { memberUser, project, schedule, tasks } from "../fixtures";

vi.mock("frappe-gantt", () => ({ default: class {} }));

const members = (role: string) => [
  { user_id: memberUser.id, email: memberUser.email, full_name: memberUser.full_name, role },
];

function projectRoutes(role: string) {
  return {
    "GET /auth/me": { body: memberUser },
    "GET /projects/5": { body: project },
    "GET /projects/5/members": { body: members(role) },
    "GET /projects/5/tasks": { body: tasks },
    "GET /projects/5/dependencies": { body: [] },
    "GET /projects/5/schedule": { body: schedule },
    "GET /projects/5/resources": { body: [] },
    "GET /projects/5/assignments": { body: [] },
  };
}

function renderProject() {
  return render(
    <MemoryRouter initialEntries={["/proyectos/5"]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("pantalla de proyecto", () => {
  beforeEach(() => {
    sessionStorage.setItem(
      "pm-web.tokens",
      JSON.stringify({ access_token: "a", refresh_token: "r" }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("un lector ve el proyecto pero no puede editar", async () => {
    installApi(projectRoutes("lector"));
    renderProject();

    expect(await screen.findByRole("heading", { name: "Migración ERP" })).toBeInTheDocument();
    expect(screen.getByText(/Tu rol: lector/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Eliminar Diseño" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar tarea" })).not.toBeInTheDocument();
  });

  it("un miembro puede editar tareas", async () => {
    installApi(projectRoutes("miembro"));
    renderProject();

    expect(await screen.findByRole("button", { name: "Eliminar Diseño" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar tarea" })).toBeInTheDocument();
  });

  it("si otra persona cambió la tarea, avisa y no sobrescribe en silencio", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    installApi({
      ...projectRoutes("miembro"),
      "DELETE /projects/5/tasks/10": { status: 409, body: { detail: "Versión vieja" } },
    });
    renderProject();

    fireEvent.click(await screen.findByRole("button", { name: "Eliminar Diseño" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Otra persona cambió esta información/,
    );
  });

  it("muestra la ruta crítica en el resumen", async () => {
    installApi(projectRoutes("miembro"));
    renderProject();

    expect(await screen.findByText(/Ruta crítica: 2 tareas/)).toBeInTheDocument();
  });
});
