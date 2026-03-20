import type { AuthProviders, AuthUser } from "@/types/auth";
import type { SessionListItem, SessionRead } from "@/types/session";
import type { RunListResponse, RunLog, ServiceInfo } from "@/types/wes";
import type { HealthResponse } from "@/types/health";
import type { SystemInfo } from "@/types/system-info";
import type { FileListResponse, FileUploadResponse } from "@/types/files";

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

// Files
export function listFiles(sessionId: string) {
  return apiFetch<FileListResponse>(
    `/api/v1/sessions/${sessionId}/files`,
  );
}

export async function uploadFiles(
  sessionId: string,
  files: File[],
): Promise<FileUploadResponse> {
  const form = new FormData();
  for (const f of files) {
    form.append("files", f);
  }
  const res = await fetch(`/api/v1/sessions/${sessionId}/files`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  return res.json();
}

export function deleteFile(sessionId: string, path: string) {
  return apiFetch<void>(
    `/api/v1/sessions/${sessionId}/files/${path}`,
    { method: "DELETE" },
  );
}

export function getFileUrl(sessionId: string, path: string, preview = false) {
  const base = `/api/v1/sessions/${sessionId}/files/${path}`;
  return preview ? `${base}?preview=true` : base;
}

// Tools & Datasets
import type { ToolListResponse, DatasetListResponse } from "@/types/tools";

export function listTools(search?: string) {
  const params = search ? `?search=${encodeURIComponent(search)}` : "";
  return apiFetch<ToolListResponse>(`/api/v1/tools${params}`);
}

export function listToolsByDomain(domain: string) {
  return apiFetch<ToolListResponse>(`/api/v1/tools/${encodeURIComponent(domain)}`);
}

export function listDatasets(search?: string) {
  const params = search ? `?search=${encodeURIComponent(search)}` : "";
  return apiFetch<DatasetListResponse>(`/api/v1/datasets${params}`);
}

// Auth
export function getAuthProviders() {
  return apiFetch<AuthProviders>("/api/v1/auth/providers");
}

export function getAuthMe() {
  return apiFetch<AuthUser>("/api/v1/auth/me");
}

export function logout() {
  return apiFetch<{ ok: boolean }>("/api/v1/auth/logout", { method: "POST" });
}

// Pipelines
import type {
  PipelineCreate,
  PipelineListItem,
  PipelineRead,
  PipelineTemplate,
} from "@/types/pipeline";

export function listPipelines(sessionId?: string) {
  const params = sessionId
    ? `?session_id=${encodeURIComponent(sessionId)}`
    : "";
  return apiFetch<PipelineListItem[]>(`/api/v1/pipelines${params}`);
}

export function getPipeline(id: string) {
  return apiFetch<PipelineRead>(`/api/v1/pipelines/${id}`);
}

export function createPipeline(data: PipelineCreate) {
  return apiFetch<PipelineRead>("/api/v1/pipelines", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function cancelPipeline(id: string) {
  return apiFetch<PipelineRead>(`/api/v1/pipelines/${id}/cancel`, {
    method: "POST",
  });
}

export function getPipelineTemplates() {
  return apiFetch<PipelineTemplate[]>("/api/v1/pipelines/templates");
}
