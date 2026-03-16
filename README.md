# orenoBiomni

Deployment, customization, and enhancement layer for [Biomni](https://github.com/snap-stanford/Biomni) — a biomedical AI agent platform.

## What is this?

This repo contains everything needed to deploy and run a customized Biomni instance:

- **Docker containers** for reproducible deployment on any GPU machine
- **Deployment scripts** for cloud GPU instances and local machines
- **Patches** to upstream Biomni for Ollama/thinking-model compatibility and Gradio 6 support
- **Terraform** templates for AWS infrastructure
- **Architecture plan** for production deployment with job scheduling, UI enhancements, and multi-user auth

## Quick Start (Docker)

```bash
# 1. Clone this repo with Biomni
git clone https://github.com/inutano/orenoBiomni.git
cd orenoBiomni
git clone https://github.com/snap-stanford/Biomni.git

# 2. Configure
cp .env.example .env
# Edit .env to set model, ports, etc.

# 3. Launch (requires NVIDIA GPU + Container Toolkit)
docker compose up -d

# UI at http://localhost:7860
```

## Quick Start (Local, no Docker)

```bash
cd orenoBiomni
git clone https://github.com/snap-stanford/Biomni.git

# Setup (installs conda, Ollama, model, patches Biomni)
bash scripts/setup-local.sh

# Launch
bash scripts/launch.sh
```

## Cloud Deploy (AWS)

```bash
# Option A: Script-based
bash scripts/deploy.sh

# Option B: Terraform
cd terraform/aws
terraform init
terraform apply \
  -var="ssh_key_name=mykey" \
  -var="allowed_cidr=203.0.113.0/24" \
  -var="vpc_id=vpc-xxx" \
  -var="subnet_id=subnet-xxx"
```

## Project Structure

```
orenoBiomni/
├── docker/
│   ├── Dockerfile            # Multi-stage: minimal (3GB) or full (13GB)
│   └── entrypoint.sh         # App entrypoint (waits for Ollama, pulls model)
├── docker-compose.yml        # app + ollama (+ postgres/redis for Phase 2)
├── .env.example              # Configuration template
├── docs/
│   └── plan.md               # Full deployment & enhancement roadmap
├── patches/
│   └── biomni-ollama-compat.patch  # Upstream Biomni patches
├── scripts/
│   ├── setup-local.sh        # Local machine setup (conda + Ollama + Biomni)
│   ├── launch.sh             # Launch Biomni with Ollama backend
│   ├── deploy.sh             # Cloud provisioning script
│   └── dgx-spark-setup.sh   # Dual DGX Spark setup (vLLM + QSFP)
└── terraform/
    └── aws/                  # EC2 GPU + security groups + EBS
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

## Roadmap

See [docs/plan.md](docs/plan.md) for the full plan:

1. **Phase 1**: Containerization & cloud deploy (Dockerfile, compose, Terraform)
2. **Phase 2**: FastAPI backend + job queue (Celery + Temporal)
3. **Phase 3**: UI enhancement (Next.js shell + Gradio chat)
4. **Phase 4**: Production hardening (monitoring, CI/CD, scaling)
