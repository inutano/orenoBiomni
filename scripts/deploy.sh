#!/bin/bash
set -e

##############################################################################
# orenoBiomni Cloud Deploy Script
# Provisions a GPU instance and launches Biomni via docker-compose
#
# Usage:
#   bash deploy.sh                    # Interactive setup
#   bash deploy.sh --skip-drivers     # Skip NVIDIA driver install
#   bash deploy.sh --build full       # Build with full bio tools
##############################################################################

BUILD_TARGET="${BUILD_TARGET:-minimal}"
SKIP_DRIVERS=false
MODEL="${BIOMNI_LLM:-qwen3.5:35b-a3b-q8_0}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-drivers) SKIP_DRIVERS=true; shift ;;
        --build) BUILD_TARGET="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=============================================="
echo "  orenoBiomni Cloud Deploy"
echo "=============================================="
echo "  Build target: $BUILD_TARGET"
echo "  Model:        $MODEL"
echo "=============================================="
echo ""

# Step 1: Detect environment
echo "[1/6] Detecting environment..."
ARCH=$(uname -m)
OS=$(uname -s)

if [ "$OS" != "Linux" ]; then
    echo "ERROR: This script is for Linux only. Use setup-local.sh for other platforms."
    exit 1
fi

echo "  Arch: $ARCH"
echo "  OS: $OS"

# Detect cloud provider
if curl -sf -m 2 http://169.254.169.254/latest/meta-data/ > /dev/null 2>&1; then
    CLOUD="aws"
elif curl -sf -m 2 -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/ > /dev/null 2>&1; then
    CLOUD="gcp"
elif curl -sf -m 2 -H "Metadata: true" "http://169.254.169.254/metadata/instance?api-version=2021-02-01" > /dev/null 2>&1; then
    CLOUD="azure"
else
    CLOUD="unknown"
fi
echo "  Cloud: $CLOUD"
echo ""

# Step 2: Install NVIDIA drivers + container toolkit
if [ "$SKIP_DRIVERS" = false ]; then
    echo "[2/6] Checking NVIDIA drivers..."
    if ! command -v nvidia-smi &>/dev/null; then
        echo "Installing NVIDIA drivers..."
        if [ "$CLOUD" = "aws" ]; then
            # AWS-optimized driver install
            sudo apt-get update
            sudo apt-get install -y linux-headers-$(uname -r)
            sudo apt-get install -y nvidia-driver-535
        else
            sudo apt-get update
            sudo apt-get install -y nvidia-driver-535
        fi
        echo "NVIDIA drivers installed. A reboot may be required."
    else
        echo "NVIDIA drivers found:"
        nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    fi

    # Install NVIDIA Container Toolkit
    if ! dpkg -l | grep -q nvidia-container-toolkit; then
        echo "Installing NVIDIA Container Toolkit..."
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
        sudo apt-get update
        sudo apt-get install -y nvidia-container-toolkit
        sudo nvidia-ctk runtime configure --runtime=docker
        sudo systemctl restart docker
        echo "NVIDIA Container Toolkit installed."
    else
        echo "NVIDIA Container Toolkit already installed."
    fi
else
    echo "[2/6] Skipping driver install."
fi
echo ""

# Step 3: Install Docker if needed
echo "[3/6] Checking Docker..."
if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed. You may need to log out and back in for group changes."
fi

if ! command -v docker compose &>/dev/null; then
    echo "Installing Docker Compose plugin..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

docker --version
docker compose version
echo ""

# Step 4: Clone Biomni if needed
echo "[4/6] Setting up project..."
cd "$PROJECT_DIR"

if [ ! -d "Biomni" ]; then
    echo "Cloning Biomni..."
    git clone https://github.com/snap-stanford/Biomni.git
fi
echo ""

# Step 5: Configure
echo "[5/6] Configuring..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    sed -i "s|^BIOMNI_LLM=.*|BIOMNI_LLM=${MODEL}|" "$PROJECT_DIR/.env"
    echo "Created .env from template."
else
    echo ".env already exists."
fi
echo ""

# Step 6: Build and launch
echo "[6/6] Building and launching..."
cd "$PROJECT_DIR"

export BUILD_TARGET
docker compose build --build-arg BUILDKIT_INLINE_CACHE=1 app
docker compose up -d

echo ""
echo "Waiting for services to start..."
sleep 5

# Check health
docker compose ps

echo ""
echo "=============================================="
echo "  orenoBiomni Deploy Complete"
echo "=============================================="
echo ""

# Get access URL
if [ "$CLOUD" = "aws" ]; then
    PUBLIC_IP=$(curl -sf http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "N/A")
    PRIVATE_IP=$(curl -sf http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "N/A")
    echo "  Public:  http://${PUBLIC_IP}:7860"
    echo "  Private: http://${PRIVATE_IP}:7860"
else
    IP=$(hostname -I | awk '{print $1}')
    echo "  URL: http://${IP}:7860"
fi

echo ""
echo "  Logs:    docker compose logs -f"
echo "  Stop:    docker compose down"
echo "  Rebuild: docker compose build app && docker compose up -d"
echo ""
