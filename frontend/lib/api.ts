/**
 * The only place in the frontend that knows the backend exists.
 *
 * Base URL always comes from NEXT_PUBLIC_API_URL (Vercel env var); every call
 * sends the session cookie, which is why the backend needs
 * `allow_credentials=True` and an explicit origin allowlist.
 */

import type {
  AnalysisDetail,
  AnalysisListItem,
  AnalysisResult,
  CV,
  ErrorCode,
  ErrorResponse,
  User,
} from "./types";

const BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

/** A typed backend failure. `code` is exhaustive, so the UI can switch on it. */
export class ApiError extends Error {
  readonly code: ErrorCode;
  readonly status: number;
  readonly detail?: Record<string, string | number> | null;

  constructor(status: number, body: ErrorResponse) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.status = status;
    this.detail = body.detail;
  }
}

/** Network-level failure (backend cold, DNS, CORS) rendered as an ApiError. */
function offlineError(): ApiError {
  return new ApiError(0, {
    code: "llm_unavailable",
    message:
      "Could not reach the server. It may be waking up from sleep - try again in a few seconds.",
  });
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        ...(init.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...init.headers,
      },
    });
  } catch {
    throw offlineError();
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    if (payload && typeof payload.code === "string") {
      throw new ApiError(response.status, payload as ErrorResponse);
    }
    throw new ApiError(response.status, {
      code: "invalid_request",
      message: `Unexpected error (${response.status}).`,
    });
  }

  return payload as T;
}

async function requestBlob(path: string, fallbackMessage = "Could not download this file."): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { credentials: "include" });
  } catch {
    throw offlineError();
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    if (payload && typeof payload.code === "string") {
      throw new ApiError(response.status, payload as ErrorResponse);
    }
    throw new ApiError(response.status, {
      code: response.status === 404 ? "not_found" : "invalid_request",
      message: response.status === 404 ? "That file does not exist." : fallbackMessage,
    });
  }
  return response.blob();
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  body: JSON.stringify(body),
});

export const api = {
  // --- auth ---
  signup: (email: string, password: string) =>
    request<User>("/auth/signup", json({ email, password })),

  login: (email: string, password: string) =>
    request<User>("/auth/login", json({ email, password })),

  forgotPassword: (email: string) =>
    request<{ ok: boolean }>("/auth/forgot-password", json({ email })),

  acceptRecoverySession: (
    accessToken: string,
    refreshToken: string,
    expiresIn: number,
  ) =>
    request<User>(
      "/auth/recovery-session",
      json({
        access_token: accessToken,
        refresh_token: refreshToken,
        expires_in: expiresIn,
      }),
    ),

  updatePassword: (password: string) =>
    request<{ ok: boolean }>("/auth/password", {
      method: "PUT",
      body: JSON.stringify({ password }),
    }),

  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),

  // Never leave the application splash screen waiting forever when the API is
  // unavailable or a browser connection gets stuck.
  me: () => request<User>("/auth/me", { signal: AbortSignal.timeout(10_000) }),

  // --- CVs ---
  listCVs: () => request<CV[]>("/cvs"),

  uploadCV: (label: string, file: File) => {
    const form = new FormData();
    form.append("label", label);
    form.append("file", file);
    return request<CV>("/cvs", { method: "POST", body: form });
  },

  deleteCV: (id: number) => request<void>(`/cvs/${id}`, { method: "DELETE" }),

  updateCV: (id: number, label: string) =>
    request<CV>(`/cvs/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ label }),
    }),

  getCVFile: (id: number, download = false) =>
    requestBlob(`/cvs/${id}/file${download ? "?download=true" : ""}`),

  // --- analyses ---
  analyze: (vacancyText: string) =>
    request<AnalysisResult>("/analyze", json({ vacancy_text: vacancyText })),

  listAnalyses: () => request<AnalysisListItem[]>("/analyses"),

  getAnalysis: (id: number) => request<AnalysisDetail>(`/analyses/${id}`),

  getAnalysisPDF: (id: number) =>
    requestBlob(`/analyses/${id}/pdf`, "Could not create the PDF report."),

  deleteAnalysis: (id: number) =>
    request<void>(`/analyses/${id}`, { method: "DELETE" }),
};
