# orenoBiomni App Container
# No GPU needed — Ollama handles model inference via HTTP
#
# Build:
#   docker build -t orenoiomni-app -f docker/Dockerfile .
#
# Two build targets:
#   --target minimal  (environment.yml only, ~3GB, fast)
#   --target full     (fixed_env.yml with bio tools, ~13GB, slow)

# =============================================================================
# Stage 1: Base with conda
# =============================================================================
FROM condaforge/miniforge3:latest AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# =============================================================================
# Stage 2a: Minimal environment (core deps only, fast build)
# =============================================================================
FROM base AS minimal-deps

COPY Biomni/biomni_env/environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml -n biomni_e1 \
    && conda clean -afy \
    && rm /tmp/environment.yml

# =============================================================================
# Stage 2b: Full environment (all bio tools, slow build)
# =============================================================================
FROM base AS full-deps

COPY Biomni/biomni_env/fixed_env.yml /tmp/fixed_env.yml
RUN conda env create -f /tmp/fixed_env.yml -n biomni_e1 \
    && conda clean -afy \
    && rm /tmp/fixed_env.yml

# =============================================================================
# Stage 3a: Minimal app
# =============================================================================
FROM minimal-deps AS minimal

COPY Biomni /app/Biomni
COPY patches /app/patches

WORKDIR /app/Biomni

# Apply patches
RUN git apply /app/patches/biomni-ollama-compat.patch 2>/dev/null || true

# Install Biomni
SHELL ["conda", "run", "-n", "biomni_e1", "/bin/bash", "-c"]
RUN pip install -e . -q

COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 7860

ENTRYPOINT ["/app/entrypoint.sh"]

# =============================================================================
# Stage 3b: Full app
# =============================================================================
FROM full-deps AS full

COPY Biomni /app/Biomni
COPY patches /app/patches

WORKDIR /app/Biomni

# Apply patches
RUN git apply /app/patches/biomni-ollama-compat.patch 2>/dev/null || true

# Install Biomni
SHELL ["conda", "run", "-n", "biomni_e1", "/bin/bash", "-c"]
RUN pip install -e . -q

COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 7860

ENTRYPOINT ["/app/entrypoint.sh"]
