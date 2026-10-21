import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, getStoredTokens, request, setStoredTokens } from "../../src/api/client";
import { installApi } from "../support/api";

describe("cliente de API", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("envía el token de acceso y devuelve el cuerpo", async () => {
    setStoredTokens({ access_token: "acceso", refresh_token: "refresco" });
    const fetchMock = installApi({ "GET /projects": { body: [{ id: 1 }] } });

    const result = await request<{ id: number }[]>("/projects");

    expect(result).toEqual([{ id: 1 }]);
    const headers = fetchMock.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer acceso");
  });

  it("lanza ApiError con el detalle del servidor", async () => {
    installApi({
      "POST /projects/1/tasks/2/move": { status: 409, body: { detail: "Versión vieja" } },
    });

    await expect(
      request("/projects/1/tasks/2/move", { method: "POST", auth: false }),
    ).rejects.toMatchObject({ status: 409, message: "Versión vieja" });
  });

  it("renueva el token una vez cuando responde 401 y reintenta", async () => {
    setStoredTokens({ access_token: "viejo", refresh_token: "refresco" });
    let calls = 0;
    installApi({
      "GET /projects": () => {
        calls += 1;
        return calls === 1 ? { status: 401, body: { detail: "expirado" } } : { body: ["ok"] };
      },
      "POST /auth/refresh": { body: { access_token: "nuevo", refresh_token: "nuevo-r" } },
    });

    const result = await request<string[]>("/projects");

    expect(result).toEqual(["ok"]);
    expect(getStoredTokens()?.access_token).toBe("nuevo");
  });

  it("cierra la sesión si el refresco también falla", async () => {
    setStoredTokens({ access_token: "viejo", refresh_token: "malo" });
    installApi({
      "GET /projects": { status: 401, body: { detail: "expirado" } },
      "POST /auth/refresh": { status: 401, body: { detail: "inválido" } },
    });

    await expect(request("/projects")).rejects.toBeInstanceOf(ApiError);
    expect(getStoredTokens()).toBeNull();
  });
});
