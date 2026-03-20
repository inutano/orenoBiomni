#!/bin/bash
set -euo pipefail

##############################################################################
# orenoBiomni Cloud Deploy Script
#
# Provisions a fresh Ubuntu or Amazon Linux instance for running orenoBiomni
# with Docker Compose. Idempotent — safe to re-run.
#
# Usage:
#   bash deploy.sh                        # Basic deploy (no GPU/ollama)
#   bash deploy.sh --gpu                  # Also start ollama service
#   bash deploy.sh --gpu --model qwen3    # Specify model to pull
#   bash deploy.sh --skip-drivers         # Skip NVIDIA driver install
#   bash deploy.sh --build full           # Build with full bio tools
#   bash deploy.sh --repo-url URL         # Custom git clone URL
#   bash deploy.sh --app-dir /opt/biomni  # Custom install directory
##############################################################################

# ── Defaults ────────────────────────────────────────────────────────────────
BUILD_TARGET="${BUILD_TARGET:-minimal}"
SKIP_DRIVERS=false
GPU_MODE=false
MODEL="${BIOMNI_LLM:-qwen3.5:35b-a3b-q8_0}"
REPO_URL="https://github.com/inutano/orenoBiomni.git"
APP_DIR=""  # auto-detected or user-specified

# ── Parse arguments ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu)          GPU_MODE=true; shift ;;
        --skip-drivers) SKIP_DRIVERS=true; shift ;;
        --build)        BUILD_TARGET="$2"; shift 2 ;;
        --model)        MODEL="$2"; shift 2 ;;
        --repo-url)     REPO_URL="$2"; shift 2 ;;
        --app-dir)      APP_DIR="$2"; shift 2 ;;
        -h|--help)
            head -18 "$0" | tail -12
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# If run from within the repo, use that directory; otherwise use --app-dir or ~/orenoBiomni
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/../docker-compose.yml" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -n "$APP_DIR" ]; then
    PROJECT_DIR="$APP_DIR"
else
    PROJECT_DIR="$HOME/orenoBiomni"
fi

# ── Logging helpers ─────────────────────────────────────────────────────────
log()  { echo -e "\033[1;34m>>>\033[0m $*"; }
warn() { echo -e "\033[1;33mWARN:\033[0m $*"; }
err()  { echo -e "\033[1;31mERROR:\033[0m $*" >&2; }

echo "=============================================="
echo "  orenoBiomni Cloud Deploy"
echo "=============================================="
echo "  Build target : $BUILD_TARGET"
echo "  GPU mode     : $GPU_MODE"
echo "  Model        : $MODEL"
echo "  Install dir  : $PROJECT_DIR"
echo "=============================================="
echo ""

###############################################################################
# Step 1: Detect OS and environment
###############################################################################
log "[1/8] Detecting environment..."

if [ "$(uname -s)" != "Linux" ]; then
    err "This script is for Linux only. Use setup-local.sh for macOS."
    exit 1
fi

ARCH=$(uname -m)
log "  Arch: $ARCH"

# Detect distro family
DISTRO="unknown"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    case "$ID" in
        ubuntu|debian)       DISTRO="debian" ;;
        amzn|amazon|al2023)  DISTRO="amzn" ;;
        rhel|centos|rocky)   DISTRO="rhel" ;;
        *)                   DISTRO="$ID" ;;
    esac
fi
log "  Distro family: $DISTRO ($PRETTY_NAME)"

# Detect cloud provider
CLOUD="unknown"
if curl -sf -m 2 http://169.254.169.254/latest/meta-data/ > /dev/null 2>&1; then
    CLOUD="aws"
elif curl -sf -m 2 -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/ > /dev/null 2>&1; then
    CLOUD="gcp"
elif curl -sf -m 2 -H "Metadata: true" "http://169.254.169.254/metadata/instance?api-version=2021-02-01" > /dev/null 2>&1; then
    CLOUD="azure"
fi
log "  Cloud: $CLOUD"

# Check for NVIDIA GPU
HAS_GPU=false
if lspci 2>/dev/null | grep -qi nvidia; then
    HAS_GPU=true
fi
log "  GPU detected: $HAS_GPU"
echo ""

###############################################################################
# Step 2: Install Docker + docker-compose plugin
###############################################################################
log "[2/8] Checking Docker..."

if ! command -v docker &>/dev/null; then
    log "Installing Docker..."
    if [ "$DISTRO" = "amzn" ]; then
        sudo yum install -y docker
        sudo systemctl enable docker
        sudo systemctl start docker
    else
        # Universal installer works for Ubuntu/Debian/RHEL/etc.
        curl -fsSL https://get.docker.com | sudo sh
    fi
    sudo usermod -aG docker "$USER"
    log "Docker installed. Group membership updated (may need re-login)."
else
    log "Docker already installed: $(docker --version)"
fi

# Ensure docker-compose plugin is available
if ! docker compose version &>/dev/null; then
    log "Installing Docker Compose plugin..."
    if [ "$DISTRO" = "amzn" ]; then
        sudo mkdir -p /usr/local/lib/docker/cli-plugins
        COMPOSE_URL="https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)"
        sudo curl -SL "$COMPOSE_URL" -o /usr/local/lib/docker/cli-plugins/docker-compose
        sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    else
        sudo apt-get update -qq
        sudo apt-get install -y -qq docker-compose-plugin
    fi
    log "Docker Compose installed: $(docker compose version)"
else
    log "Docker Compose available: $(docker compose version)"
fi
echo ""

###############################################################################
# Step 3: Install NVIDIA drivers + container toolkit (if GPU present)
###############################################################################
log "[3/8] NVIDIA setup..."

if [ "$HAS_GPU" = true ] && [ "$SKIP_DRIVERS" = false ]; then
    # Install NVIDIA drivers if not present
    if ! command -v nvidia-smi &>/dev/null; then
        log "Installing NVIDIA drivers..."
        if [ "$DISTRO" = "debian" ]; then
            sudo apt-get update -qq
            sudo apt-get install -y -qq linux-headers-"$(uname -r)"
            sudo apt-get install -y -qq nvidia-driver-535
        elif [ "$DISTRO" = "amzn" ]; then
            sudo yum install -y kernel-devel-"$(uname -r)" gcc
            # Amazon Linux 2: use NVIDIA CUDA repo
            sudo yum install -y nvidia-driver-latest-dkms
        fi
        warn "NVIDIA drivers installed. A reboot may be required."
    else
        log "NVIDIA drivers found:"
        nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null || true
    fi

    # Install NVIDIA Container Toolkit
    if ! command -v nvidia-ctk &>/dev/null; then
        log "Installing NVIDIA Container Toolkit..."
        if [ "$DISTRO" = "debian" ]; then
            curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
                sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg 2>/dev/null
            curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
                sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
                sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null
            sudo apt-get update -qq
            sudo apt-get install -y -qq nvidia-container-toolkit
        elif [ "$DISTRO" = "amzn" ]; then
            curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
                sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo > /dev/null
            sudo yum install -y nvidia-container-toolkit
        fi
        sudo nvidia-ctk runtime configure --runtime=docker
        sudo systemctl restart docker
        log "NVIDIA Container Toolkit installed."
    else
        log "NVIDIA Container Toolkit already installed."
    fi
elif [ "$SKIP_DRIVERS" = true ]; then
    log "Skipping driver install (--skip-drivers)."
else
    log "No GPU detected, skipping driver install."
fi
echo ""

###############################################################################
# Step 4: Clone repo if needed
###############################################################################
log "[4/8] Setting up project directory..."

if [ ! -d "$PROJECT_DIR" ]; then
    log "Cloning orenoBiomni to $PROJECT_DIR..."
    git clone "$REPO_URL" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# Clone Biomni subproject if not present
if [ ! -d "$PROJECT_DIR/Biomni" ]; then
    log "Cloning Biomni..."
    git clone https://github.com/snap-stanford/Biomni.git "$PROJECT_DIR/Biomni"
fi
echo ""

###############################################################################
# Step 5: Generate .env with random passwords
###############################################################################
log "[5/8] Configuring environment..."

if [ ! -f "$PROJECT_DIR/.env" ]; then
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
    REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)

    log "Generating .env from .env.example with random passwords..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"

    # Set random passwords
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" "$PROJECT_DIR/.env"
    sed -i "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=${REDIS_PASSWORD}|" "$PROJECT_DIR/.env"
    sed -i "s|^REDIS_URL=.*|REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0|" "$PROJECT_DIR/.env"

    # Set model
    sed -i "s|^BIOMNI_LLM=.*|BIOMNI_LLM=${MODEL}|" "$PROJECT_DIR/.env"

    # In production, remove direct host-port bindings for postgres/redis
    sed -i "s|^POSTGRES_PORT=.*|POSTGRES_PORT=|" "$PROJECT_DIR/.env"
    sed -i "s|^REDIS_PORT=.*|REDIS_PORT=|" "$PROJECT_DIR/.env"

    log "Generated .env with random credentials."
else
    log ".env already exists, skipping generation."
fi

# Create secrets directory for prod compose
mkdir -p "$PROJECT_DIR/secrets"
if [ ! -f "$PROJECT_DIR/secrets/postgres_password" ]; then
    grep '^POSTGRES_PASSWORD=' "$PROJECT_DIR/.env" | cut -d= -f2 > "$PROJECT_DIR/secrets/postgres_password"
    chmod 600 "$PROJECT_DIR/secrets/postgres_password"
fi
if [ ! -f "$PROJECT_DIR/secrets/redis_password" ]; then
    grep '^REDIS_PASSWORD=' "$PROJECT_DIR/.env" | cut -d= -f2 > "$PROJECT_DIR/secrets/redis_password"
    chmod 600 "$PROJECT_DIR/secrets/redis_password"
fi
echo ""

###############################################################################
# Step 6: Generate self-signed SSL certificate
###############################################################################
log "[6/8] SSL certificates..."

SSL_DIR="$PROJECT_DIR/ssl"
mkdir -p "$SSL_DIR"

if [ ! -f "$SSL_DIR/server.crt" ]; then
    log "Generating self-signed SSL certificate..."
    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout "$SSL_DIR/server.key" \
        -out "$SSL_DIR/server.crt" \
        -subj "/C=US/ST=California/L=Stanford/O=orenoBiomni/CN=localhost" \
        2>/dev/null
    chmod 600 "$SSL_DIR/server.key"
    log "Self-signed certificate generated at $SSL_DIR/"
    warn "Replace with a real certificate for production use."
else
    log "SSL certificate already exists, skipping."
fi
echo ""

###############################################################################
# Step 7: Build and pull Docker images
###############################################################################
log "[7/8] Building Docker images..."

cd "$PROJECT_DIR"

# Determine compose command
COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# Pull pre-built images
$COMPOSE_CMD pull postgres redis || true

# Build application images
export BUILD_TARGET
$COMPOSE_CMD build

if [ "$GPU_MODE" = true ]; then
    $COMPOSE_CMD --profile gpu pull ollama || true
fi

echo ""

###############################################################################
# Step 8: Start services
###############################################################################
log "[8/8] Starting services..."

# Start core services (postgres, redis first for health checks)
$COMPOSE_CMD up -d postgres redis
log "Waiting for database and cache to become healthy..."
sleep 5

# Start backend (runs migrations via entrypoint), worker, frontend, nginx
$COMPOSE_CMD up -d backend worker frontend nginx

# Start ollama if GPU mode
if [ "$GPU_MODE" = true ]; then
    $COMPOSE_CMD --profile gpu up -d ollama
    log "Ollama started. Pulling model $MODEL (this may take a while)..."
    # Wait for Ollama to be ready
    OLLAMA_URL="http://localhost:${OLLAMA_PORT:-11434}"
    for i in $(seq 1 30); do
        if curl -sf "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
            break
        fi
        sleep 2
    done
    docker compose exec ollama ollama pull "$MODEL" || warn "Failed to pull model. Pull manually: docker compose exec ollama ollama pull $MODEL"
fi

log "Waiting for all services to start..."
sleep 5

# Show service status
$COMPOSE_CMD ps

echo ""
echo "=============================================="
echo "  orenoBiomni Deploy Complete"
echo "=============================================="
echo ""

# Determine access URLs
if [ "$CLOUD" = "aws" ]; then
    PUBLIC_IP=$(curl -sf -m 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "N/A")
    PRIVATE_IP=$(curl -sf -m 2 http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "N/A")
elif [ "$CLOUD" = "gcp" ]; then
    PUBLIC_IP=$(curl -sf -m 2 -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || echo "N/A")
    PRIVATE_IP=$(curl -sf -m 2 -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/instance/network-interfaces/0/ip 2>/dev/null || echo "N/A")
else
    PUBLIC_IP="N/A"
    PRIVATE_IP=$(hostname -I | awk '{print $1}')
fi

echo "  HTTPS:   https://${PUBLIC_IP}/"
echo "  HTTP:    http://${PUBLIC_IP}/"
if [ "$PRIVATE_IP" != "N/A" ]; then
    echo "  Private: https://${PRIVATE_IP}/"
fi
echo "  API:     https://${PUBLIC_IP}/api/health"
echo "  Docs:    https://${PUBLIC_IP}/docs"
echo ""
echo "  Note: Using self-signed SSL certificate."
echo "        Your browser will show a security warning."
echo ""
echo "  Logs:      $COMPOSE_CMD logs -f"
echo "  Stop:      $COMPOSE_CMD down"
echo "  Rebuild:   $COMPOSE_CMD build && $COMPOSE_CMD up -d"
echo "  GPU start: $COMPOSE_CMD --profile gpu up -d ollama"
echo ""
