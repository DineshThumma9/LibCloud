import type {
  OpsCredentials,
  OpsDetailKind,
  OpsDetailsResponse,
  OpsRunDetailResponse,
  OpsRunsResponse,
  OpsSearchResponse,
  OpsSummary,
} from "./types";

const STORAGE_KEY = "libcloud.ops.credentials";
export const UNAUTHORIZED_EVENT = "libcloud:ops-unauthorized";

export class OpsApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "OpsApiError";
    this.status = status;
  }
}

export function describeError(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "Something went wrong.";
}

export function loadCredentials(): OpsCredentials | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<OpsCredentials>;
    if (!parsed.username || typeof parsed.password !== "string") return null;
    return { username: parsed.username, password: parsed.password };
  } catch {
    return null;
  }
}

export function saveCredentials(credentials: OpsCredentials): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(credentials));
}

export function clearCredentials(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

function toBase64(value: string): string {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function authHeader(credentials: OpsCredentials): string {
  return `Basic ${toBase64(`${credentials.username}:${credentials.password}`)}`;
}

async function readError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
  } catch {
    // response was not JSON
  }
  return `Request failed (HTTP ${response.status}).`;
}

function handleUnauthorized(response: Response): void {
  if (response.status !== 401) return;
  clearCredentials();
  window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}

async function opsRequest<T>(
  credentials: OpsCredentials,
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  headers.set("Authorization", authHeader(credentials));

  const response = await fetch(`/api/ops${path}`, {
    ...init,
    headers,
    cache: "no-store",
    // Suppress the browser's native Basic auth prompt on 401; the login gate
    // wants the JSON error instead.
    credentials: "omit",
  });

  if (!response.ok) {
    handleUnauthorized(response);
    throw new OpsApiError(response.status, await readError(response));
  }

  return (await response.json()) as T;
}

function withQuery(path: string, query: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === "") continue;
    params.set(key, String(value));
  }
  const suffix = params.toString();
  return suffix ? `${path}?${suffix}` : path;
}

export async function getSummary(credentials: OpsCredentials): Promise<OpsSummary> {
  return opsRequest<OpsSummary>(credentials, "/summary");
}

export async function getRuns(
  credentials: OpsCredentials,
  options: { username?: string; limit?: number } = {}
): Promise<OpsRunsResponse> {
  return opsRequest<OpsRunsResponse>(
    credentials,
    withQuery("/runs", {
      username: options.username?.trim().toLowerCase() || undefined,
      limit: options.limit ?? 200,
    })
  );
}

export async function getRun(
  credentials: OpsCredentials,
  runId: string
): Promise<OpsRunDetailResponse> {
  return opsRequest<OpsRunDetailResponse>(
    credentials,
    `/runs/${encodeURIComponent(runId)}`
  );
}

export async function getDetails(
  credentials: OpsCredentials,
  kind: OpsDetailKind,
  options: { username?: string; limit?: number } = {}
): Promise<OpsDetailsResponse> {
  return opsRequest<OpsDetailsResponse>(
    credentials,
    withQuery(`/details/${kind}`, {
      username: options.username?.trim().toLowerCase() || undefined,
      limit: options.limit ?? 2000,
    })
  );
}

export async function searchRunDetails(
  credentials: OpsCredentials,
  query: string,
  limit = 200
): Promise<OpsSearchResponse> {
  return opsRequest<OpsSearchResponse>(
    credentials,
    withQuery("/search", { q: query.trim(), limit })
  );
}

export async function downloadRunCsv(
  credentials: OpsCredentials,
  runId: string,
  kind: OpsDetailKind
): Promise<void> {
  const response = await fetch(
    `/api/ops/runs/${encodeURIComponent(runId)}/${kind}.csv`,
    {
      headers: {
        Accept: "text/csv",
        Authorization: authHeader(credentials),
      },
      cache: "no-store",
      credentials: "omit",
    }
  );

  if (!response.ok) {
    handleUnauthorized(response);
    throw new OpsApiError(response.status, await readError(response));
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  const filename = match?.[1] ?? `${runId}-${kind}.csv`;
  const blobUrl = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
}
