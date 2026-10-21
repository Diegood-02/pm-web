import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { downloadFile } from "../../src/api/client";
import { App } from "../../src/App";
import { AuthProvider } from "../../src/auth/AuthContext";
import { installApi } from "../support/api";
import { adminUser, project } from "../fixtures";

vi.mock("frappe-gantt", () => ({ default: class {} }));

describe("descarga de archivos", () => {
  beforeEach(() => {
    sessionStorage.setItem(
      "pm-web.tokens",
      JSON.stringify({ access_token: "a", refresh_token: "r" }),
    );
    URL.createObjectURL = vi.fn(() => "blob:prueba");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("usa el nombre de archivo que indica el servidor", async () => {
    const clicked: string[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clicked.push(this.download);
    });
    installApi({});
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(new Blob(["x,y"], { type: "text/csv" }), {
            status: 200,
            headers: { "Content-Disposition": 'attachment; filename="cronograma-5.csv"' },
          }),
      ),
    );

    await downloadFile("/projects/5/export/schedule.csv", "respaldo.csv");

    expect(clicked).toEqual(["cronograma-5.csv"]);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:prueba");
  });

  it("lanza el error del servidor si la descarga falla", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "Proyecto no encontrado" }), { status: 404 }),
      ),
    );

    await expect(downloadFile("/projects/9/export/schedule.csv", "x.csv")).rejects.toMatchObject({
      status: 404,
      message: "Proyecto no encontrado",
    });
  });
});

describe("importación de proyectos", () => {
  beforeEach(() => {
    sessionStorage.setItem(
      "pm-web.tokens",
      JSON.stringify({ access_token: "a", refresh_token: "r" }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  it("un archivo JSON válido crea el proyecto y lo muestra en la lista", async () => {
    const fetchMock = installApi({
      "GET /auth/me": { body: adminUser },
      "GET /projects": { body: [] },
      "POST /projects/import": {
        status: 201,
        body: { ...project, id: 8, name: "Copia de Migración" },
      },
    });
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );

    const input = await screen.findByLabelText("Archivo JSON exportado desde PM Web");
    const file = new File(
      [JSON.stringify({ format: "pm-web-project", schema_version: 1 })],
      "p.json",
      {
        type: "application/json",
      },
    );
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Proyecto importado: Copia de Migración.",
    );
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) => String(url).endsWith("/projects/import") && init?.method === "POST",
        ),
      ).toBe(true),
    );
  });

  it("un archivo que no es JSON se rechaza sin llamar a la API", async () => {
    const fetchMock = installApi({
      "GET /auth/me": { body: adminUser },
      "GET /projects": { body: [] },
    });
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>,
    );

    const input = await screen.findByLabelText("Archivo JSON exportado desde PM Web");
    fireEvent.change(input, { target: { files: [new File(["no json"], "p.txt")] } });

    expect(await screen.findByRole("alert")).toHaveTextContent("El archivo no es JSON válido.");
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });
});
