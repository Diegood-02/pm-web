// Modo demo para GitHub Pages: responde las rutas GET con datos de ejemplo guardados en
// snapshot.json (generado desde la API real). No hay servidor: cualquier correo y contraseña
// entran, y las escrituras se rechazan con 403.

import snapshotJson from "./snapshot.json";
import { DEMO_READONLY_MESSAGE } from "./flags";

interface DemoSnapshot {
  generated_at: string;
  status_date: string;
  note: string;
  responses: Record<string, unknown>;
}

const snapshot = snapshotJson as DemoSnapshot;

export const DEMO_STATUS_DATE = snapshot.status_date;

const DEMO_TOKENS = {
  access_token: "demo-acceso",
  refresh_token: "demo-refresco",
  token_type: "bearer",
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Responde una ruta de la API (sin prefijo /api/v1 y sin query string). Es pura y se puede probar. */
export function demoRoute(method: string, path: string): Response {
  if (path === "/auth/login" || path === "/auth/refresh") {
    return method === "POST"
      ? jsonResponse(200, DEMO_TOKENS)
      : jsonResponse(405, { detail: "Método no permitido" });
  }
  if (method !== "GET") {
    return jsonResponse(403, { detail: DEMO_READONLY_MESSAGE });
  }
  if (Object.prototype.hasOwnProperty.call(snapshot.responses, path)) {
    return jsonResponse(200, snapshot.responses[path]);
  }
  return jsonResponse(404, { detail: "Esta vista no está disponible en la demo" });
}

/** Reemplaza fetch para las llamadas a la API; el resto de peticiones (fuentes, imágenes) siguen igual. */
export function installDemoApi(apiBase: string): void {
  const realFetch = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.startsWith(apiBase)) {
      return realFetch(input, init);
    }
    const path = url.slice(apiBase.length).split("?")[0];
    const method = (init?.method ?? "GET").toUpperCase();
    return Promise.resolve(demoRoute(method, path));
  };
}
