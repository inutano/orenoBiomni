export type State =
  | "UNKNOWN"
  | "QUEUED"
  | "INITIALIZING"
  | "RUNNING"
  | "PAUSED"
  | "COMPLETE"
  | "EXECUTOR_ERROR"
  | "SYSTEM_ERROR"
  | "CANCELED"
  | "CANCELING"
  | "PREEMPTED";

export const TERMINAL_STATES: State[] = [
  "COMPLETE",
  "EXECUTOR_ERROR",
  "SYSTEM_ERROR",
  "CANCELED",
  "PREEMPTED",
];

export interface RunSummary {
  run_id: string;
  state: State;
  start_time: string | null;
  end_time: string | null;
  tags: Record<string, string>;
}

export interface Log {
  name: string | null;
  cmd: string[] | null;
  start_time: string | null;
  end_time: string | null;
  stdout: string | null;
  stderr: string | null;
  exit_code: number | null;
  system_logs: string[] | null;
}

export interface RunRequest {
  workflow_type: string | null;
  workflow_params: Record<string, unknown> | null;
  tags: Record<string, string> | null;
}

export interface RunLog {
  run_id: string;
  request: RunRequest | null;
  state: State;
  run_log: Log | null;
  task_logs_url: string | null;
  outputs: Record<string, unknown> | null;
}

export interface RunListResponse {
  runs: RunSummary[];
  next_page_token: string | null;
}

export interface ServiceInfo {
  workflow_type_versions: Record<string, { workflow_type_version: string[] }>;
  supported_wes_versions: string[];
  workflow_engine_versions: Record<string, string>;
  system_state_counts: Record<string, number>;
  tags: Record<string, string>;
}
