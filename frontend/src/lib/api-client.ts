import type { SessionListItem, SessionRead } from "@/types/session";
import type { RunListResponse, RunLog, ServiceInfo } from "@/types/wes";
import type { HealthResponse } from "@/types/health";
import type { SystemInfo } from "@/types/system-info";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Sessions
export function createSession(title?: string) {
  return apiFetch<SessionListItem>("/api/v1/sessions", {
    method: "POST",
    body: JSON.stringify({ title: title || null }),
  });
}

export function listSessions(limit = 50) {
  return apiFetch<SessionListItem[]>(`/api/v1/sessions?limit=${limit}`);
}

export function getSession(id: string) {
  return apiFetch<SessionRead>(`/api/v1/sessions/${id}`);
}

export function deleteSession(id: string) {
  return apiFetch<void>(`/api/v1/sessions/${id}`, { method: "DELETE" });
}

// WES
export function listRuns(sessionId?: string, pageSize = 20) {
  const params = new URLSearchParams({ page_size: String(pageSize) });
  if (sessionId) params.set("session_id", sessionId);
  return apiFetch<RunListResponse>(`/ga4gh/wes/v1/runs?${params}`);
}

export function getRun(runId: string) {
  return apiFetch<RunLog>(`/ga4gh/wes/v1/runs/${runId}`);
}

export function cancelRun(runId: string) {
  return apiFetch<{ run_id: string }>(`/ga4gh/wes/v1/runs/${runId}/cancel`, {
    method: "POST",
  });
}

export function getServiceInfo() {
  return apiFetch<ServiceInfo>("/ga4gh/wes/v1/service-info");
}

// Health
export function getHealth() {
  return apiFetch<HealthResponse>("/api/v1/health");
}

// System info
export function getSystemInfo() {
  return apiFetch<SystemInfo>("/api/v1/system-info");
}
