export interface ModelInfo {
  name: string;
  family: string | null;
  parameter_size: string | null;
  quantization: string | null;
  context_length: number | null;
  experts: string | null;
  format: string | null;
}

export interface OllamaInfo {
  version: string | null;
  model_loaded: boolean;
  model_size_gb: number | null;
  vram_used_gb: number | null;
  gpu_layers: number | null;
  gpu_count: number | null;
}

export interface WorkerInfo {
  celery_active: boolean;
  task_timeout: number;
  concurrency: string | null;
}

export interface GpuDevice {
  name: string;
  memory_total_mb: number;
  memory_used_mb: number | null;
}

export interface GpuInfo {
  driver_version: string | null;
  devices: GpuDevice[];
}

export interface SystemInfo {
  model: ModelInfo;
  source: string;
  ollama: OllamaInfo | null;
  gpu: GpuInfo | null;
  worker: WorkerInfo;
  timeout_seconds: number;
  version: string;
}
