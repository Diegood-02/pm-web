import { vi } from "vitest";

export interface MockResult {
  status?: number;
  body?: unknown;
}

export type MockHandler = (request: { method: string; body: unknown }) => MockResult;

/** Instala un fetch falso. Las rutas se indexan como "METODO /ruta" (sin prefijo /api/v1 ni query). */
export function installApi(routes: Record<string, MockHandler | MockResult>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input));
    const method = init?.method ?? "GET";
    const key = `${method} ${url.pathname.replace("/api/v1", "")}`;
    const entry = routes[key];
    if (entry === undefined) {
      throw new Error(`Sin ruta simulada para ${key}`);
    }
    const body = init?.body ? (JSON.parse(String(init.body)) as unknown) : undefined;
    const result: MockResult = typeof entry === "function" ? entry({ method, body }) : entry;
    const status = result.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(result.body ?? null), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
