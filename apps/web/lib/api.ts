export const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "") + "/api/v1";

const ACCESS_TOKEN_KEY = "careerintel_access_token";
const CSRF_TOKEN_KEY = "careerintel_csrf_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setStoredSession(accessToken: string, csrfToken?: string | null): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  if (csrfToken) {
    window.sessionStorage.setItem(CSRF_TOKEN_KEY, csrfToken);
  }
}

export function clearStoredSession(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  window.sessionStorage.removeItem(CSRF_TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const csrf = typeof window !== "undefined" ? window.sessionStorage.getItem(CSRF_TOKEN_KEY) : null;
  const headers = new Headers(options.headers || {});

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (csrf) {
    headers.set("X-CSRF-Token", csrf);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const errBody = await res.json();
      if (typeof errBody?.detail === "string") {
        detail = errBody.detail;
      } else if (Array.isArray(errBody?.detail) && errBody.detail[0]?.msg) {
        detail = errBody.detail.map((d: { msg: string }) => d.msg).join("; ");
      }
    } catch {
      // keep fallback message
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export async function apiDownload(path: string, fallbackFilename: string): Promise<void> {
  const token = getStoredToken();
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    credentials: "include",
  });
  if (!res.ok) {
    throw new ApiError(`Download failed (${res.status})`, res.status);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fallbackFilename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
