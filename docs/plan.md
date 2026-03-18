# orenoBiomni: Deployment & Enhancement Plan

## Design Decisions

- **Frontend**: Mixed — Gradio for chat/agent, Next.js for shell (session mgmt, tool browser, job dashboard)
- **Cloud**: Cloud-agnostic, start with AWS
- **Users**: University-internal, public within campus network
- **Auth**: OAuth via Google and GitHub accounts
- **Network**: Restricted to university network (VPN/IP allowlist)
- **Workflows**: Both single-step tool calls and multi-step pipelines
- **Job API**: GA4GH Workflow Execution Service (WES) v1.1.0 compatible

## Architecture

```
                    University Network / VPN
                           |
                    +------v------+
                    |  Nginx/ALB  | <- IP allowlist
                    |  + OAuth    | <- Google/GitHub SSO
                    +------+------+
                           |
              +------------+------------+
              |            |            |
        +-----v-----+ +---v----+ +-----v-----+
        |  Next.js   | | Gradio | |  FastAPI   |
        |  Shell UI  | | Chat   | |  Backend   |
        | (sessions, | | (agent | | (WES API,  |
        |  tools,    | |  chat) | |  auth,     |
        |  dashboard)| |        | |  storage)  |
        +------------+ +---+----+ +-----+------+
                           |            |
                      +----v------------v----+
                      |   A1 Agent (LangGraph)|
                      +-----------+----------+
                                  |
                      +-----------v----------+
                      |   Celery + Redis      |
                      |   (WES execution)     |
                      +----+-----------+-----+
                           |           |
                    +------v--+  +-----v----+
                    | Worker  |  | Worker   |
                    | (Python |  | (CLI/R   |
                    |  tools) |  |  tools)  |
                    | Docker  |  | Docker   |
                    +---------+  +----------+
                           |
              +------------+------------+
              |            |            |
        +-----v-----+ +---v----+ +-----v-----+
        | PostgreSQL | | Redis  | | S3/MinIO  |
        | (sessions, | | (queue,| | (data lake|
        |  users,    | |  cache)| |  outputs) |
        |  history)  | |        | |           |
        +-----------+  +--------+ +-----------+
                           |
                    +------v------+
                    | Ollama/vLLM |
                    | (GPU node)  |
                    +-------------+
```

## Phase 1: Containerization & Cloud Deploy — COMPLETE

### Deliverables

- [x] `Dockerfile` — multi-stage: `minimal` (~3GB) and `full` (~17GB) targets
- [x] `docker-compose.yml` — app + ollama (GPU), postgres/redis ready for Phase 2
- [x] `deploy.sh` — cloud provisioning (detect GPU/cloud, install drivers, Docker, NVIDIA toolkit)
- [x] Terraform templates for AWS (EC2 GPU + security group with CIDR restrict + EBS)
- [x] Data lake: lazy-download from S3 on first use (already supported upstream)
- [x] `entrypoint.sh` — waits for Ollama, auto-pulls model, pre-warms, then launches
- [x] Ollama service tuning (flash attention, q8_0 KV cache, keep-alive, bind 0.0.0.0)

### Tested

- [x] `minimal` image builds and runs (~2min build)
- [x] `full` image builds (~17GB with all bio tools)
- [x] App container connects to Ollama, pre-warms model, serves Gradio UI (HTTP 200)
- [ ] `deploy.sh` on cloud instance (needs actual cloud infra)
- [ ] Terraform apply on AWS (needs AWS credentials)

### Key Decisions

- Base image: `condaforge/miniforge3` (app doesn't need GPU — Ollama handles inference)
- Using official `ollama/ollama` image instead of custom Dockerfile.ollama
- Separate containers for app and model serving
- Two build targets: `minimal` (environment.yml) or `full` (fixed_env.yml with bio tools)

## Phase 2: Backend API + Job Queue — COMPLETE

### Phase 2a: FastAPI Backend — COMPLETE

- [x] Wrap A1 agent as API endpoints (`/api/v1/chat`, `/api/v1/sessions`)
- [x] Session CRUD (create, list, load, delete) backed by PostgreSQL
- [x] SSE streaming for agent chat responses
- [x] Alembic migrations auto-run on startup

### Phase 2b: Celery + Redis Job Queue — COMPLETE

- [x] **Celery + Redis** for single-step tool execution
  - Single worker container with Python/R/bash capability
  - Worker runs in Docker container with resource limits (4 CPU, 8GB memory)
  - Monkey-patched `run_with_timeout` dispatches to Celery transparently
  - Per-session workspace volumes for artifact capture
- [x] **GA4GH WES v1.1.0 compatible API** at `/ga4gh/wes/v1/`
  - `GET /service-info` — capabilities, state counts, engine info
  - `GET/POST /runs` — list and submit runs with token-based pagination
  - `GET /runs/{id}` — full RunLog with stdout/stderr/exit_code
  - `GET /runs/{id}/status` — lightweight state-only endpoint
  - `GET /runs/{id}/tasks` — task listing per run
  - `POST /runs/{id}/cancel` — cancel with Celery revocation
- [x] WES State enum: QUEUED → RUNNING → COMPLETE / EXECUTOR_ERROR / CANCELED
- [x] Redis pub/sub for job status notifications
- [x] Graceful fallback: runs in-process if Redis is unavailable

### Key Decisions (Phase 2)

- Monkey-patch approach: no upstream Biomni changes needed
- `contextvars.ContextVar` propagates session_id to patched execution functions
- Python state does NOT persist between `<execute>` calls (each is a separate Celery task) — safer isolation
- Sync `psycopg2` for Celery workers (Celery is sync, cannot use asyncpg)
- WES API alongside internal session/chat API — agent-driven runs and direct WES submissions both produce WES-compatible records

### Remaining (Phase 2c — future)

- [ ] **Temporal** for multi-step pipelines
  - Define pipeline templates (e.g., scRNA-seq: load -> QC -> normalize -> cluster -> annotate)
  - Allow agent to compose pipelines dynamically
  - Durable execution with retry, resume, and visibility

## Phase 3: UI Enhancement

### Phase 3a: Next.js Shell

- [ ] **Project setup**: Next.js 15 + Tailwind CSS + shadcn/ui
- [ ] **Layout**: Sidebar + main content area
- [ ] **Session panel**: List/create/delete sessions, conversation history
- [ ] **Chat interface**: SSE-backed chat with the agent (replaces Gradio iframe)
- [ ] **Run dashboard**: WES runs — queued/running/completed with logs, stdout/stderr, artifacts
- [ ] **Settings**: Model selector, temperature, tool retriever toggle

### Phase 3b: Auth Integration

- [ ] OAuth2 via NextAuth.js (Google + GitHub providers)
- [ ] Session tokens passed to FastAPI backend
- [ ] Per-user conversation isolation
- [ ] User management API in backend

### Phase 3c: Enhanced Features

- [ ] **Tool browser**: Searchable list of Biomni tool modules + data lake datasets
- [ ] **File manager**: Upload datasets, view generated plots/tables, download results
- [ ] File upload/download API (`/api/v1/files`)
- [ ] Inline plot gallery (rendered from workspace artifacts)
- [ ] One-click PDF report export

## Phase 4: Production Hardening (ongoing)

- [ ] **Monitoring**: Prometheus metrics, Grafana dashboards (GPU util, job throughput, latency)
- [ ] **Logging**: Structured logging (JSON), centralized collection (CloudWatch or ELK)
- [ ] **Rate limiting**: Per-user request limits, concurrent job limits
- [ ] **CI/CD**: GitHub Actions — lint, test, build Docker images, deploy
- [ ] **Backup**: PostgreSQL snapshots, conversation history export
- [ ] **Security**: Input sanitization, code execution audit log, network policies
- [ ] **Scaling**: Horizontal worker scaling (K8s HPA or ECS auto-scaling)
- [ ] **Documentation**: API docs (OpenAPI), user guide, admin guide

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend shell | Next.js 15 + Tailwind CSS + shadcn/ui |
| Agent chat | SSE streaming (replaces Gradio iframe) |
| Backend API | FastAPI + Pydantic |
| Job execution | GA4GH WES v1.1.0 API + Celery |
| Auth | NextAuth.js (Google/GitHub OAuth) |
| Database | PostgreSQL |
| Cache/Queue | Redis |
| Workflow | Celery (single-step) + Temporal (multi-step pipelines, future) |
| Object storage | S3 (AWS) / MinIO (self-hosted) |
| Model serving | Ollama or vLLM |
| Container runtime | Docker + docker-compose (dev), ECS/K8s (prod) |
| IaC | Terraform (AWS) |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus + Grafana |

## Upstream Biomni Patches (maintained in patches/)

1. `a1.py`: `<think>` tag stripping in generate/execute nodes (for thinking models like Qwen3.5)
2. `a1.py`: Ollama XML tag hint in system prompt
3. `a1.py`: Gradio 6 compat (removed deprecated args, added strict_cors/ssr_mode)
4. `llm.py`: ChatOllama with `reasoning=False`, `num_ctx=65536`
