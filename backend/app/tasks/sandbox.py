"""Ephemeral Docker container execution for sandboxed code runs."""

import logging

import docker
from docker.errors import APIError, ImageNotFound

from ..config import settings

logger = logging.getLogger(__name__)

# Map job types to sandbox images and execution commands
_IMAGE_MAP = {
    "python": lambda: settings.sandbox_image_python,
    "r": lambda: settings.sandbox_image_r,
    "bash": lambda: settings.sandbox_image_bash,
}

_CMD_MAP = {
    "python": ["python", "/tmp/run.py"],
    "r": ["Rscript", "/tmp/run.R"],
    "bash": ["bash", "/tmp/run.sh"],
}

_FILE_MAP = {
    "python": "/tmp/run.py",
    "r": "/tmp/run.R",
    "bash": "/tmp/run.sh",
}


def _get_docker_client() -> docker.DockerClient:
    """Create a Docker client from the default socket."""
    return docker.from_env()


def run_in_sandbox(
    job_id: str,
    session_id: str,
    code: str,
    job_type: str,
    timeout: int,
) -> tuple[str, str, int]:
    """Run code in an ephemeral Docker container.

    Returns (stdout, stderr, exit_code).
    """
    if job_type not in _IMAGE_MAP:
        raise ValueError(f"Unsupported job type: {job_type}")

    image = _IMAGE_MAP[job_type]()
    cmd = _CMD_MAP[job_type]
    script_path = _FILE_MAP[job_type]
    container_name = f"sandbox-{job_id[:8]}"
    workspace_host = f"{settings.workspace_base_path}/{session_id}"

    client = _get_docker_client()
    container = None

    try:
        # Write code to a temp script via a shell wrapper so it ends up inside
        # the container at the expected path, then execute it.
        # The heredoc delimiter is single-quoted to prevent variable expansion.
        shell_cmd = f"cat > {script_path} << 'ORENOEOF'\n{code}\nORENOEOF\n" + " ".join(cmd)

        nano_cpus = int(settings.sandbox_cpus * 1e9)

        container = client.containers.create(
            image=image,
            command=["bash", "-c", shell_cmd],
            name=container_name,
            working_dir="/workspace",
            volumes={
                workspace_host: {"bind": "/workspace", "mode": "rw"},
                "biomni-data": {"bind": "/app/Biomni/data", "mode": "ro"},
            },
            nano_cpus=nano_cpus,
            mem_limit=settings.sandbox_memory,
            network_disabled=settings.sandbox_network_disabled,
            tmpfs={"/tmp": f"size={settings.sandbox_tmpfs_size}"},
            auto_remove=False,  # We remove manually after capturing logs
            detach=True,
        )

        logger.info(
            "Starting sandbox container %s (image=%s, type=%s) for job %s",
            container_name, image, job_type, job_id,
        )
        container.start()

        # Wait for completion with timeout
        try:
            result = container.wait(timeout=timeout)
            exit_code = result.get("StatusCode", -1)
        except Exception as wait_err:
            # Timeout or connection error — kill the container
            logger.warning(
                "Sandbox container %s timed out or errored for job %s: %s",
                container_name, job_id, wait_err,
            )
            try:
                container.kill()
            except Exception:
                pass
            return (
                "",
                f"Execution timed out after {timeout}s",
                137,
            )

        # Capture logs
        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

        logger.info(
            "Sandbox container %s finished for job %s with exit_code=%d",
            container_name, job_id, exit_code,
        )
        return (stdout, stderr, exit_code)

    except ImageNotFound:
        msg = f"Sandbox image '{image}' not found. Build it first: docker compose build sandbox"
        logger.error(msg)
        return ("", msg, 1)

    except APIError as e:
        msg = f"Docker API error: {e}"
        logger.exception("Docker API error for job %s", job_id)
        return ("", msg, 1)

    except Exception as e:
        msg = f"Sandbox execution error: {e}"
        logger.exception("Unexpected sandbox error for job %s", job_id)
        return ("", msg, 1)

    finally:
        # Always clean up the container
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                logger.debug("Container %s already removed or cleanup failed", container_name)
