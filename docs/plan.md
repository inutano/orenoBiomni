# orenoBiomni: Deployment & Enhancement Plan

## Design Decisions

- **Frontend**: Mixed — Gradio for chat/agent, Next.js for shell (session mgmt, tool browser, job dashboard)
- **Cloud**: Cloud-agnostic, start with AWS
- **Users**: University-internal, public within campus network
- **Auth**: OAuth via Google and GitHub accounts
- **Network**: Restricted to university network (VPN/IP allowlist)
- **Workflows**: Both single-step tool calls and multi-step pipelines

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
        | (sessions, | | (agent | | (jobs API, |
        |  tools,    | |  chat) | |  auth,     |
        |  dashboard)| |        | |  storage)  |
        +------------+ +---+----+ +-----+------+
                           |            |
                      +----v------------v----+
                      |   A1 Agent (LangGraph)|
                      +-----------+----------+
                                  |
                      +-----------v----------+
                      |   Temporal / Celery   |
                      |   Workflow Engine     |
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
- [ ] User management (OAuth tokens, preferences) — deferred to Phase 3
- [ ] File upload/download API (`/api/v1/files`) — deferred to Phase 3

### Phase 2b: Celery + Redis Job Queue — COMPLETE

- [x] **Celery + Redis** for single-step tool execution
  - Single worker container with Python/R/bash capability
  - Worker runs in Docker container with resource limits (4 CPU, 8GB memory)
  - Monkey-patched `run_with_timeout` dispatches to Celery transparently
  - Per-session workspace volumes for artifact capture
- [x] Job management API (`/api/v1/jobs`) — list, get, cancel
- [x] Job tracking in PostgreSQL (status, code, result, artifacts, timing, worker_id)
- [x] Redis pub/sub for job status notifications
- [x] Graceful fallback: runs in-process if Redis is unavailable

### Key Decisions (Phase 2b)

- Monkey-patch approach: no upstream Biomni changes needed
- `contextvars.ContextVar` propagates session_id to patched execution functions
- Python state does NOT persist between `<execute>` calls (each is a separate Celery task) — safer isolation
- Sync `psycopg2` for Celery workers (Celery is sync, cannot use asyncpg)

### Remaining (Phase 2c — future)

- [ ] **Temporal** for multi-step pipelines
  - Define pipeline templates (e.g., scRNA-seq: load -> QC -> normalize -> cluster -> annotate)
  - Allow agent to compose pipelines dynamically
  - Durable execution with retry, resume, and visibility

## Phase 3: UI Enhancement (2-3 weeks)

### Next.js Shell (wraps Gradio via iframe or API)

- [ ] **Layout**: Sidebar + main content area
- [ ] **Session panel**: List/create/delete sessions, conversation history
- [ ] **Tool browser**: Searchable list of 24 tool modules + data lake datasets
- [ ] **Job dashboard**: Running/queued/completed jobs with logs, output, artifacts
- [ ] **File manager**: Upload datasets, view generated plots/tables, download results
- [ ] **Settings**: Model selector, temperature, tool retriever toggle

### Gradio Enhancements (within existing UI)

- [ ] Better code display in executor panel (syntax highlighting)
- [ ] Progress indicators for long-running tools
- [ ] Inline plot gallery (not just chat messages)
- [ ] One-click PDF report export

### Auth Integration

- [ ] OAuth2 via NextAuth.js (Google + GitHub providers)
- [ ] Session tokens passed to FastAPI backend
- [ ] Per-user conversation isolation

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
| Frontend shell | Next.js + Tailwind CSS |
| Agent chat | Gradio (embedded) |
| Backend API | FastAPI + Pydantic |
| Auth | NextAuth.js (Google/GitHub OAuth) |
| Database | PostgreSQL |
| Cache/Queue | Redis |
| Workflow | Celery (single-step) + Temporal (multi-step pipelines) |
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
