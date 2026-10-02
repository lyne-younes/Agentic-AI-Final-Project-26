// Every backend call goes through /api, proxied to FastAPI by Vite (dev) or nginx (Docker).
const API_BASE = "/api";

/** Full-page navigation target: the OAuth flow leaves the SPA and returns via the callback. */
export const LOGIN_URL = `${API_BASE}/auth/login`;

/** Dispatched on window when any request comes back 401 (see main.tsx). */
export const UNAUTHORIZED_EVENT = "api:unauthorized";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), { credentials: "same-origin", ...init });
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response));
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export function sendJson<T>(path: string, method: "POST" | "PATCH", body: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** Turns FastAPI's `{"detail": ...}` error bodies into a message fit for the UI. */
async function errorMessage(response: Response): Promise<string> {
  const fallback =
    response.status >= 500
      ? "Something went wrong on our side. Please try again."
      : `Request failed (${response.status}).`;
  try {
    const { detail } = (await response.json()) as { detail?: unknown };
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item: { msg?: string }) => (item.msg ?? "").replace(/^Value error, /, ""))
        .filter(Boolean);
      if (messages.length > 0) return messages.join(" ");
    }
  } catch {
    // Not a JSON body (e.g. a proxy error page).
  }
  return fallback;
}
