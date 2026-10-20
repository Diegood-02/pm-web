import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../../src/App";
import { AuthProvider } from "../../src/auth/AuthContext";
import { installApi } from "../support/api";
import { adminUser, memberUser } from "../fixtures";

vi.mock("frappe-gantt", () => ({ default: class {} }));

function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

const tokens = { access_token: "acceso", refresh_token: "refresco", token_type: "bearer" };

describe("flujo de login", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("entra con credenciales válidas y muestra la lista de proyectos", async () => {
    installApi({
      "POST /auth/login": { body: tokens },
      "GET /auth/me": { body: memberUser },
      "GET /projects": { body: [] },
    });
    renderApp("/login");

    fireEvent.change(screen.getByLabelText("Correo electrónico"), {
      target: { value: "miembro@ejemplo.com" },
    });
    fireEvent.change(screen.getByLabelText("Contraseña"), {
      target: { value: "contraseña-segura-123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("heading", { name: "Proyectos" })).toBeInTheDocument();
    expect(screen.getByText("Mario Miembro")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Usuarios" })).not.toBeInTheDocument();
  });

  it("muestra un error claro con contraseña incorrecta", async () => {
    installApi({
      "POST /auth/login": { status: 401, body: { detail: "Correo o contraseña incorrectos" } },
    });
    renderApp("/login");

    fireEvent.change(screen.getByLabelText("Correo electrónico"), {
      target: { value: "miembro@ejemplo.com" },
    });
    fireEvent.change(screen.getByLabelText("Contraseña"), {
      target: { value: "mala-clave-123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Correo o contraseña incorrectos.");
    expect(sessionStorage.getItem("pm-web.tokens")).toBeNull();
  });

  it("una ruta protegida sin sesión lleva al login", async () => {
    renderApp("/");

    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
  });

  it("solo el admin ve la sección de usuarios", async () => {
    sessionStorage.setItem(
      "pm-web.tokens",
      JSON.stringify({ access_token: "a", refresh_token: "r" }),
    );
    installApi({
      "GET /auth/me": { body: adminUser },
      "GET /projects": { body: [] },
    });
    renderApp("/");

    expect(await screen.findByRole("link", { name: "Usuarios" })).toBeInTheDocument();
  });
});
