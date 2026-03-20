import logging
import subprocess

import httpx

from fastapi import APIRouter

from ..config import settings
from ..schemas.system_info import (
    GpuDevice,
    GpuInfo,
    ModelInfo,
    OllamaInfo,
    SystemInfoResponse,
    WorkerInfo,
)
from ..services import agent_manager

logger = logging.getLogger(__name__)
router = APIRouter()

_OLLAMA_TIMEOUT = 5.0


async def _fetch_ollama_info() -> OllamaInfo:
    """Gather version, running model, and GPU info from the Ollama API."""
    info = OllamaInfo()
    base = settings.ollama_base_url

    async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
        # Version
        try:
            r = await client.get(f"{base}/api/version")
            info.version = r.json().get("version")
        except Exception:
            logger.debug("Could not fetch Ollama version")

        # Running models (gpu/vram info)
        try:
            r = await client.get(f"{base}/api/ps")
            models = r.json().get("models", [])
            if models:
                m = models[0]  # Primary model
                info.model_loaded = True
                size_bytes = m.get("size", 0)
                vram_bytes = m.get("size_vram", 0)
                if size_bytes:
                    info.model_size_gb = round(size_bytes / (1024**3), 1)
                if vram_bytes:
                    info.vram_used_gb = round(vram_bytes / (1024**3), 1)
                details = m.get("details", {})
                if "gpu_count" in details:
                    info.gpu_count = details["gpu_count"]
        except Exception:
            logger.debug("Could not fetch Ollama running models")

    return info


async def _fetch_model_info() -> ModelInfo:
    """Fetch model metadata from Ollama's /api/show endpoint."""
    model = ModelInfo(name=settings.biomni_llm)
    if settings.biomni_source != "Ollama":
        return model

    base = settings.ollama_base_url
    try:
        async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
            r = await client.post(
                f"{base}/api/show",
                json={"model": settings.biomni_llm},
            )
            data = r.json()
            details = data.get("model_info", {})

            arch = details.get("general.architecture", "")
            model.family = details.get("general.basename") or arch

            # Parameter size
            param_count = details.get("general.parameter_count")
            if param_count:
                if param_count >= 1_000_000_000:
                    model.parameter_size = f"{param_count / 1_000_000_000:.1f}B"
                else:
                    model.parameter_size = f"{param_count / 1_000_000:.0f}M"

            # Quantization — prefer tag hint, fall back to metadata
            tag_parts = settings.biomni_llm.split(":")
            if len(tag_parts) > 1:
                tag = tag_parts[-1].upper()
                for q in ("Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q4_0", "F16", "F32"):
                    if q in tag:
                        model.quantization = q
                        break

            # Context length — try arch-prefixed key first, then generic
            ctx = (
                details.get(f"{arch}.context_length")
                or details.get("llama.context_length")
                or details.get("context_length")
            )
            if ctx:
                model.context_length = int(ctx)

            # Expert info (MoE models) — try arch-prefixed keys
            expert_count = (
                details.get(f"{arch}.expert_count")
                or details.get("llama.expert_count")
            )
            expert_used = (
                details.get(f"{arch}.expert_used_count")
                or details.get("llama.expert_used_count")
            )
            if expert_count:
                if expert_used:
                    model.experts = f"{expert_used}/{expert_count} active"
                else:
                    model.experts = str(expert_count)

    except Exception:
        logger.debug("Could not fetch model details from Ollama")

    return model


def _query_gpu_info() -> GpuInfo | None:
    """Query GPU info via nvidia-smi. Returns None if not available."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        devices = []
        driver = None
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                devices.append(
                    GpuDevice(
                        name=parts[0],
                        memory_total_mb=int(float(parts[1])),
                        memory_used_mb=int(float(parts[2])),
                    )
                )
                driver = parts[3]

        return GpuInfo(
            driver_version=driver,
            devices=devices,
        )
    except FileNotFoundError:
        logger.debug("nvidia-smi not found")
        return None
    except Exception:
        logger.debug("Failed to query GPU info", exc_info=True)
        return None


@router.get("/system-info", response_model=SystemInfoResponse)
async def system_info():
    model = await _fetch_model_info()

    ollama_info = None
    if settings.biomni_source == "Ollama":
        ollama_info = await _fetch_ollama_info()

    gpu = _query_gpu_info()

    worker = WorkerInfo(
        celery_active=agent_manager.is_celery_active(),
        task_timeout=settings.celery_task_timeout,
    )

    return SystemInfoResponse(
        model=model,
        source=settings.biomni_source,
        ollama=ollama_info,
        gpu=gpu,
        worker=worker,
        timeout_seconds=settings.biomni_timeout_seconds,
        version="0.1.0",
    )
