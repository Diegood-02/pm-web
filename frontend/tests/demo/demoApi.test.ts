import { afterEach, describe, expect, it, vi } from "vitest";

import { demoRoute, installDemoApi } from "../../src/demo/demoApi";
import { DEMO_READONLY_MESSAGE } from "../../src/demo/flags";
import snapshotJson from "../../src/demo/snapshot.json";

const responses: Record<string, unknown> = snapshotJson.responses;

describe("demoRoute", () => {
  it("devuelve los datos de ejemplo guardados para una ruta GET", async () => {
    const response = demoRoute("GET", "/projects");

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(responses["/projects"]);
  });

  it("entra con cualquier credencial y devuelve tokens de demo", async () => {
    const response = demoRoute("POST", "/auth/login");

    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({ token_type: "bearer" });
  });

  it("rechaza cualquier escritura con 403 y el mensaje de solo lectura", async () => {
    const response = demoRoute("PATCH", "/projects/42/tasks/1");

    expect(response.status).toBe(403);
    expect(await response.json()).toEqual({ detail: DEMO_READONLY_MESSAGE });
  });

  it("responde 404 para rutas que no están en el snapshot", async () => {
    const response = demoRoute("GET", "/projects/999/tasks");

    expect(response.status).toBe(404);
  });

  it("el snapshot incluye el cronograma y el costo del proyecto de ejemplo", () => {
    const projectIds = Object.keys(responses).filter((key) => /^\/projects\/\d+$/.test(key));
    expect(projectIds).toHaveLength(1);
    const id = projectIds[0];

    expect(responses[`${id}/schedule`]).toHaveProperty("critical_path");
    expect(responses[`${id}/costs`]).toHaveProperty("summary");
  });
});

describe("installDemoApi", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("intercepta solo las llamadas a la API y deja pasar el resto", async () => {
    const realFetch = vi.fn(async () => new Response("recurso real"));
    vi.stubGlobal("fetch", realFetch);
    installDemoApi("http://localhost:8000/api/v1");

    const apiResponse = await window.fetch("http://localhost:8000/api/v1/projects");
    const staticResponse = await window.fetch("/assets/logo.svg");

    expect(apiResponse.status).toBe(200);
    expect(await apiResponse.json()).toEqual(responses["/projects"]);
    expect(realFetch).toHaveBeenCalledTimes(1);
    expect(await staticResponse.text()).toBe("recurso real");
  });
});
