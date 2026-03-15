# orenoBiomni

Deployment, customization, and enhancement layer for [Biomni](https://github.com/snap-stanford/Biomni) — a biomedical AI agent platform.

## What is this?

This repo contains everything needed to deploy and run a customized Biomni instance:

- **Deployment scripts** for cloud GPU instances and local machines
- **Patches** to upstream Biomni for Ollama/thinking-model compatibility and Gradio 6 support
- **Architecture plan** for production deployment with job scheduling, UI enhancements, and multi-user auth

## Quick Start (Local)

```bash
# 1. Clone Biomni
git clone https://github.com/snap-stanford/Biomni.git
cd Biomni

# 2. Apply patches
git apply ../patches/biomni-ollama-compat.patch

# 3. Run setup
bash ../scripts/setup-local.sh

# 4. Launch
bash ../scripts/launch.sh
```

## Project Structure

```
orenoBiomni/
├── docs/
│   └── plan.md              # Full deployment & enhancement roadmap
├── patches/
│   └── biomni-ollama-compat.patch  # Upstream Biomni patches
├── scripts/
│   ├── setup-local.sh        # Local machine setup (conda + ollama + biomni)
│   ├── launch.sh             # Launch Biomni with Ollama backend
│   └── dgx-spark-setup.sh   # Dual DGX Spark setup (vLLM + QSFP)
└── README.md
```

## Roadmap

See [docs/plan.md](docs/plan.md) for the full plan:

1. **Phase 1**: Containerization & cloud deploy (Dockerfile, compose, Terraform)
2. **Phase 2**: FastAPI backend + job queue (Celery + Temporal)
3. **Phase 3**: UI enhancement (Next.js shell + Gradio chat)
4. **Phase 4**: Production hardening (monitoring, CI/CD, scaling)
