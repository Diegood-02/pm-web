import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { App } from "../src/App";
import { AuthProvider } from "../src/auth/AuthContext";

vi.mock("frappe-gantt", () => ({ default: class {} }));

describe("App", () => {
  it("sin sesión muestra la pantalla de login", async () => {
    sessionStorage.clear();
    render(
      <MemoryRouter initialEntries={["/proyectos/1"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
  });
});
