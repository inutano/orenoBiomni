from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str
    family: str | None = None
    parameter_size: str | None = None
    quantization: str | None = None
    context_length: int | None = None
    experts: str | None = None  # e.g. "8/256 active"
    format: str | None = None


class OllamaInfo(BaseModel):
    version: str | None = None
    model_loaded: bool = False
    model_size_gb: float | None = None
    vram_used_gb: float | None = None
    gpu_layers: int | None = None
    gpu_count: int | None = None


class WorkerInfo(BaseModel):
    celery_active: bool = False
    task_timeout: int = 600
    concurrency: str | None = None


class GpuDevice(BaseModel):
    name: str
    memory_total_mb: int
    memory_used_mb: int | None = None


class GpuInfo(BaseModel):
    driver_version: str | None = None
    devices: list[GpuDevice] = []


class SystemInfoResponse(BaseModel):
    model: ModelInfo
    source: str  # "Ollama", "Anthropic", "OpenAI", etc.
    ollama: OllamaInfo | None = None
    gpu: GpuInfo | None = None
    worker: WorkerInfo
    timeout_seconds: int = 600
    version: str = "0.1.0"
