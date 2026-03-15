#!/bin/bash
set -e

##############################################################################
# orenoBiomni Local Setup Script
# Sets up Biomni with Ollama on a local GPU machine
#
# Prerequisites: NVIDIA GPU with drivers installed, internet access
#
# Usage:
#   bash setup-local.sh [--model MODEL] [--biomni-dir DIR]
#
# Examples:
#   bash setup-local.sh
#   bash setup-local.sh --model qwen3.5:35b-a3b-q8_0
#   bash setup-local.sh --model qwen3.5:27b --biomni-dir ~/Biomni
##############################################################################

# Defaults
MODEL="${MODEL:-qwen3.5:35b-a3b-q8_0}"
BIOMNI_DIR="${BIOMNI_DIR:-$(pwd)/Biomni}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model) MODEL="$2"; shift 2 ;;
        --biomni-dir) BIOMNI_DIR="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "=============================================="
echo "  orenoBiomni Local Setup"
echo "=============================================="
echo "  Model:      $MODEL"
echo "  Biomni dir: $BIOMNI_DIR"
echo "=============================================="
echo ""

# Step 1: Check GPU
echo "[1/6] Checking GPU..."
if ! command -v nvidia-smi &>/dev/null; then
    echo "ERROR: nvidia-smi not found. Install NVIDIA drivers first."
    exit 1
fi
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo ""

# Step 2: Install Miniforge if needed
echo "[2/6] Checking conda..."
if ! command -v conda &>/dev/null; then
    echo "Installing Miniforge..."
    ARCH=$(uname -m)
    wget -q "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-${ARCH}.sh" -O /tmp/miniforge.sh
    bash /tmp/miniforge.sh -b -p "$HOME/miniforge3"
    rm -f /tmp/miniforge.sh
    eval "$($HOME/miniforge3/bin/conda shell.bash hook)"
    conda init bash
    echo "Miniforge installed. You may need to restart your shell."
else
    echo "conda found: $(conda --version)"
    eval "$(conda shell.bash hook)"
fi
echo ""

# Step 3: Install/update Ollama
echo "[3/6] Checking Ollama..."
if ! command -v ollama &>/dev/null; then
    echo "Installing Ollama (requires sudo)..."
    curl -fsSL https://ollama.com/install.sh | sudo sh
else
    OLLAMA_VERSION=$(ollama --version | grep -oP '[\d.]+')
    echo "Ollama found: v${OLLAMA_VERSION}"
    # Check if version is too old (< 0.5)
    MAJOR=$(echo "$OLLAMA_VERSION" | cut -d. -f1)
    MINOR=$(echo "$OLLAMA_VERSION" | cut -d. -f2)
    if [ "$MAJOR" -eq 0 ] && [ "$MINOR" -lt 5 ]; then
        echo "Ollama version too old, updating (requires sudo)..."
        curl -fsSL https://ollama.com/install.sh | sudo sh
    fi
fi
echo ""

# Step 4: Pull model
echo "[4/6] Pulling model: $MODEL ..."
ollama pull "$MODEL"
echo ""

# Step 5: Clone and patch Biomni
echo "[5/6] Setting up Biomni..."
if [ ! -d "$BIOMNI_DIR" ]; then
    git clone https://github.com/snap-stanford/Biomni.git "$BIOMNI_DIR"
fi
cd "$BIOMNI_DIR"

# Apply patches
PATCH_FILE="$PROJECT_DIR/patches/biomni-ollama-compat.patch"
if [ -f "$PATCH_FILE" ]; then
    echo "Applying patches..."
    git apply "$PATCH_FILE" 2>/dev/null && echo "Patches applied." || echo "Patches already applied or conflict (check manually)."
fi

# Create conda environment
if ! conda env list | grep -q "biomni_e1"; then
    echo "Creating conda environment (this may take a few minutes)..."
    conda env create -f biomni_env/environment.yml -y
else
    echo "Conda environment biomni_e1 already exists."
fi

# Install Biomni
eval "$(conda shell.bash hook)"
conda activate biomni_e1
pip install -e . -q
echo ""

# Step 6: Configure
echo "[6/6] Configuring..."
cat > "$BIOMNI_DIR/.env" <<EOF
# orenoBiomni configuration
BIOMNI_DATA_PATH=./data
BIOMNI_TIMEOUT_SECONDS=600
EOF

echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "  Launch Biomni:"
echo "    bash $PROJECT_DIR/scripts/launch.sh --model $MODEL --biomni-dir $BIOMNI_DIR"
echo ""
echo "  Or manually:"
echo "    conda activate biomni_e1"
echo "    cd $BIOMNI_DIR"
echo "    python -c \"from biomni.agent import A1; A1(llm='$MODEL', source='Ollama', expected_data_lake_files=[], use_tool_retriever=False).launch_gradio_demo()\""
echo ""
