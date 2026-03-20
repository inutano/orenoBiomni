import type { State } from "./wes";

export interface PipelineStep {
  name: string;
  job_type: string;
  code: string;
  depends_on: number[];
}

export interface StepResult {
  index: number;
  name: string;
  job_type: string;
  code: string;
  depends_on: number[];
  job_id: string | null;
  state: State;
  stdout: string | null;
  stderr: string | null;
  exit_code: number | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface PipelineRead {
  id: string;
  name: string;
  description: string | null;
  state: State;
  steps: StepResult[];
  current_step: number;
  total_steps: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface PipelineListItem {
  id: string;
  name: string;
  state: State;
  current_step: number;
  total_steps: number;
  created_at: string;
}

export interface PipelineCreate {
  name: string;
  description?: string;
  session_id: string;
  steps: PipelineStep[];
}

export interface PipelineTemplate {
  name: string;
  description: string;
  steps: PipelineStep[];
}
