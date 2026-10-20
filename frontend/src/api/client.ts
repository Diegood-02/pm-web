// Cliente HTTP para la API. Guarda los tokens solo en sessionStorage (por pestaña)
// y renueva el token de acceso una vez cuando la API responde 401.

const API_BASE: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
const TOKEN_KEY = "pm-web.tokens";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface StoredTokens {
  access_token: string;
  refresh_token: string;
}

export function getStoredTokens(): StoredTokens | null {
  try {
    const raw = sessionStorage.getItem(TOKEN_KEY);
    return raw ? (JSON.parse(raw) as StoredTokens) : null;
  } catch {
    return null;
  }
}

export function setStoredTokens(tokens: StoredTokens | null): void {
  try {
    if (tokens) {
      sessionStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
    } else {
      sessionStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // Sin almacenamiento disponible (p. ej. modo privado): la sesión dura solo esta carga.
  }
}

function messageFromBody(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item: { msg?: string }) => item.msg ?? "Dato no válido").join(". ");
    }
  }
  return fallback;
}

let refreshing: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const stored = getStoredTokens();
  if (!stored) return false;
  if (!refreshing) {
    refreshing = fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: stored.refresh_token }),
    })
      .then(async (response) => {
        if (!response.ok) {
          setStoredTokens(null);
          return false;
        }
        const tokens = (await response.json()) as StoredTokens;
        setStoredTokens(tokens);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const send = (): Promise<Response> => {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const token = getStoredTokens()?.access_token;
    if (auth && token) headers["Authorization"] = `Bearer ${token}`;
    return fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  };

  let response = await send();
  if (response.status === 401 && auth && (await refreshAccessToken())) {
    response = await send();
  }
  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, messageFromBody(payload, "No se pudo completar la acción"));
  }
  return payload as T;
}
