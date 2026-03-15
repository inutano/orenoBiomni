#!/bin/bash
set -e

##############################################################################
# DGX Spark Dual-Node Setup Script
# Sets up: Tailscale, QSFP networking, vLLM (distributed), Biomni
#
# Architecture:
#   Mac (Tailscale) --> Spark A (Tailscale) ←QSFP 200Gb/s→ Spark B (Tailscale)
#                         ├── Biomni UI (:7860)
#                         └── vLLM API (:8000, TP=2)
#
# Usage:
#   1. Run on each Spark after first-boot setup is complete
#      bash dgx-spark-setup.sh phase1          # On both Sparks
#   2. Connect QSFP cable, then:
#      bash dgx-spark-setup.sh phase2-node1    # On Spark A
#      bash dgx-spark-setup.sh phase2-node2    # On Spark B
#   3. Set up vLLM cluster:
#      bash dgx-spark-setup.sh phase3-head     # On Spark A
#      bash dgx-spark-setup.sh phase3-worker   # On Spark B
#   4. Launch vLLM model:
#      bash dgx-spark-setup.sh phase4          # On Spark A
#   5. Install Biomni:
#      bash dgx-spark-setup.sh phase5          # On Spark A
##############################################################################

VLLM_VERSION="26.01-py3"
VLLM_IMAGE="nvcr.io/nvidia/vllm:${VLLM_VERSION}"
MODEL="meta-llama/Llama-3.3-70B-Instruct"
QSFP_IF="enP2p1s0f1np1"
NODE1_QSFP_IP="192.168.100.10"
NODE2_QSFP_IP="192.168.100.11"
VLLM_PORT=8000
BIOMNI_PORT=7860

case "$1" in

##############################################################################
phase1)
# Phase 1: Base setup (run on BOTH Sparks after first boot)
##############################################################################
echo "=== Phase 1: Base Setup ==="

# Update system
echo "[1/5] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Ensure Docker is ready
echo "[2/5] Configuring Docker..."
sudo usermod -aG docker $USER
echo "Docker group added. You may need to log out and back in."

# Install useful tools
echo "[3/5] Installing utilities..."
sudo apt install -y curl wget git net-tools htop

# Install Tailscale
echo "[4/5] Installing Tailscale..."
if ! command -v tailscale &>/dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
    echo ""
    echo ">>> Run 'sudo tailscale up' and authenticate via the URL it prints. <<<"
    echo ">>> Do this NOW before continuing to the next phase. <<<"
    sudo tailscale up
else
    echo "Tailscale already installed."
    tailscale status || echo "Run 'sudo tailscale up' to connect."
fi

# Install Miniforge (conda) for Biomni later
echo "[5/5] Installing Miniforge..."
if ! command -v conda &>/dev/null; then
    wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh -O /tmp/miniforge.sh
    bash /tmp/miniforge.sh -b -p $HOME/miniforge3
    $HOME/miniforge3/bin/conda init bash
    rm /tmp/miniforge.sh
    echo "Miniforge installed. Run 'source ~/.bashrc' to activate."
else
    echo "Conda already installed, skipping."
fi

echo ""
echo "=== Phase 1 Complete ==="
echo ""
echo "Tailscale IP:"
tailscale ip -4 2>/dev/null || echo "  (run 'sudo tailscale up' first)"
echo ""
echo "LAN IP:"
ip -4 addr show | grep "inet " | grep -v "127.0.0.1\|docker\|br-"
echo ""
echo "Next steps:"
echo "  1. Verify Tailscale is connected: tailscale status"
echo "  2. Connect QSFP cable between the two Sparks"
echo "  3. Run 'bash dgx-spark-setup.sh phase2-node1' on Spark A"
echo "  4. Run 'bash dgx-spark-setup.sh phase2-node2' on Spark B"
;;

##############################################################################
phase2-node1)
# Phase 2a: QSFP network setup for Node 1 (Spark A)
##############################################################################
echo "=== Phase 2: QSFP Network - Node 1 (Spark A) ==="

# Configure QSFP interface
echo "[1/3] Configuring QSFP interface..."
sudo ip addr add ${NODE1_QSFP_IP}/24 dev ${QSFP_IF} 2>/dev/null || echo "IP already assigned"
sudo ip link set ${QSFP_IF} up

# Make persistent via netplan
echo "[2/3] Creating persistent netplan config..."
sudo tee /etc/netplan/40-cx7.yaml > /dev/null <<EOF
network:
  version: 2
  ethernets:
    ${QSFP_IF}:
      addresses:
        - ${NODE1_QSFP_IP}/24
      mtu: 9000
EOF
sudo chmod 600 /etc/netplan/40-cx7.yaml
sudo netplan apply

# Generate SSH key for inter-node communication
echo "[3/3] Setting up SSH keys..."
if [ ! -f ~/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
fi
echo ""
echo "=== Phase 2 Node 1 Complete ==="
echo "Copy your public key to Node 2:"
echo "  ssh-copy-id \$(whoami)@${NODE2_QSFP_IP}"
echo ""
echo "Then test: ping -c 3 ${NODE2_QSFP_IP}"
;;

##############################################################################
phase2-node2)
# Phase 2b: QSFP network setup for Node 2 (Spark B)
##############################################################################
echo "=== Phase 2: QSFP Network - Node 2 (Spark B) ==="

echo "[1/3] Configuring QSFP interface..."
sudo ip addr add ${NODE2_QSFP_IP}/24 dev ${QSFP_IF} 2>/dev/null || echo "IP already assigned"
sudo ip link set ${QSFP_IF} up

echo "[2/3] Creating persistent netplan config..."
sudo tee /etc/netplan/40-cx7.yaml > /dev/null <<EOF
network:
  version: 2
  ethernets:
    ${QSFP_IF}:
      addresses:
        - ${NODE2_QSFP_IP}/24
      mtu: 9000
EOF
sudo chmod 600 /etc/netplan/40-cx7.yaml
sudo netplan apply

echo "[3/3] Setting up SSH keys..."
if [ ! -f ~/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
fi
echo ""
echo "=== Phase 2 Node 2 Complete ==="
echo "Copy your public key to Node 1:"
echo "  ssh-copy-id \$(whoami)@${NODE1_QSFP_IP}"
echo ""
echo "Then test: ping -c 3 ${NODE1_QSFP_IP}"
;;

##############################################################################
phase3-head)
# Phase 3a: vLLM cluster - Head node (Spark A)
##############################################################################
echo "=== Phase 3: vLLM Cluster - Head Node ==="

echo "[1/3] Pulling vLLM container..."
docker pull ${VLLM_IMAGE}

echo "[2/3] Downloading cluster script..."
wget -q -O run_cluster.sh https://raw.githubusercontent.com/vllm-project/vllm/refs/heads/main/examples/online_serving/run_cluster.sh
chmod +x run_cluster.sh

echo "[3/3] Starting head node..."
export MN_IF_NAME=${QSFP_IF}
export VLLM_HOST_IP=${NODE1_QSFP_IP}

bash run_cluster.sh ${VLLM_IMAGE} ${VLLM_HOST_IP} --head ~/.cache/huggingface \
    -e VLLM_HOST_IP=${VLLM_HOST_IP} \
    -e NCCL_SOCKET_IFNAME=${MN_IF_NAME} \
    -e GLOO_SOCKET_IFNAME=${MN_IF_NAME} \
    -e OMPI_MCA_btl_tcp_if_include=${MN_IF_NAME} \
    -e TP_SOCKET_IFNAME=${MN_IF_NAME} \
    -e RAY_memory_monitor_refresh_ms=0 \
    -e MASTER_ADDR=${VLLM_HOST_IP}

echo ""
echo "=== Head node started ==="
echo "Now run 'bash dgx-spark-setup.sh phase3-worker' on Spark B"
;;

##############################################################################
phase3-worker)
# Phase 3b: vLLM cluster - Worker node (Spark B)
##############################################################################
echo "=== Phase 3: vLLM Cluster - Worker Node ==="

echo "[1/3] Pulling vLLM container..."
docker pull ${VLLM_IMAGE}

echo "[2/3] Downloading cluster script..."
wget -q -O run_cluster.sh https://raw.githubusercontent.com/vllm-project/vllm/refs/heads/main/examples/online_serving/run_cluster.sh
chmod +x run_cluster.sh

echo "[3/3] Starting worker node..."
export MN_IF_NAME=${QSFP_IF}
export VLLM_HOST_IP=${NODE2_QSFP_IP}
export HEAD_NODE_IP=${NODE1_QSFP_IP}

bash run_cluster.sh ${VLLM_IMAGE} ${HEAD_NODE_IP} --worker ~/.cache/huggingface \
    -e VLLM_HOST_IP=${VLLM_HOST_IP} \
    -e NCCL_SOCKET_IFNAME=${MN_IF_NAME} \
    -e GLOO_SOCKET_IFNAME=${MN_IF_NAME} \
    -e OMPI_MCA_btl_tcp_if_include=${MN_IF_NAME} \
    -e TP_SOCKET_IFNAME=${MN_IF_NAME} \
    -e RAY_memory_monitor_refresh_ms=0 \
    -e MASTER_ADDR=${HEAD_NODE_IP}

echo ""
echo "=== Worker node started ==="
echo "Now run 'bash dgx-spark-setup.sh phase4' on Spark A to launch the model"
;;

##############################################################################
phase4)
# Phase 4: Download model and launch vLLM inference server
##############################################################################
echo "=== Phase 4: Launch vLLM Model Server ==="

# Verify cluster
echo "[1/3] Verifying cluster..."
VLLM_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E '^node-[0-9]+$' | head -1)
if [ -z "$VLLM_CONTAINER" ]; then
    echo "ERROR: No vLLM container found. Run phase3-head first."
    exit 1
fi
docker exec ${VLLM_CONTAINER} ray status
echo ""

# Download model (requires HuggingFace login for gated models)
echo "[2/3] Downloading model: ${MODEL}..."
echo "If this is a gated model, you need to run 'huggingface-cli login' first."
docker exec ${VLLM_CONTAINER} huggingface-cli download ${MODEL} || {
    echo ""
    echo "Model download failed. For gated models, run:"
    echo "  docker exec -it ${VLLM_CONTAINER} huggingface-cli login"
    echo "Then re-run this phase."
    exit 1
}

# Launch inference server with tensor parallelism across 2 nodes
echo "[3/3] Launching vLLM server (TP=2, max_model_len=65536)..."
docker exec -d ${VLLM_CONTAINER} vllm serve ${MODEL} \
    --tensor-parallel-size 2 \
    --max_model_len 65536 \
    --host 0.0.0.0 \
    --port ${VLLM_PORT}

echo ""
echo "Waiting for server to start..."
sleep 30

# Test
echo "Testing inference..."
curl -s http://localhost:${VLLM_PORT}/v1/models | python3 -m json.tool 2>/dev/null && echo "vLLM server is ready!" || echo "Server still starting, wait a bit and test with: curl http://localhost:${VLLM_PORT}/v1/models"

TAILSCALE_IP=$(tailscale ip -4 2>/dev/null)
echo ""
echo "=== Phase 4 Complete ==="
echo "vLLM API (local):     http://localhost:${VLLM_PORT}/v1"
echo "vLLM API (Tailscale): http://${TAILSCALE_IP}:${VLLM_PORT}/v1"
echo ""
echo "Next: bash dgx-spark-setup.sh phase5"
;;

##############################################################################
phase5)
# Phase 5: Install Biomni on Spark A
##############################################################################
echo "=== Phase 5: Install Biomni ==="

# Activate conda
eval "$(${HOME}/miniforge3/bin/conda shell.bash hook)"

echo "[1/4] Cloning Biomni..."
cd $HOME
if [ ! -d "Biomni" ]; then
    git clone https://github.com/snap-stanford/Biomni.git
fi
cd Biomni

echo "[2/4] Creating conda environment..."
conda env create -f biomni_env/environment.yml -y 2>/dev/null || echo "Environment already exists"
conda activate biomni_e1

echo "[3/4] Installing Biomni..."
pip install -e . 2>/dev/null
pip install "gradio>=5.0,<6.0" 2>/dev/null

echo "[4/4] Configuring Biomni for vLLM backend..."

# Create .env
cat > .env <<EOF
# Biomni Configuration - Using local vLLM server
# No API key needed - using local model via vLLM
BIOMNI_DATA_PATH=./data
BIOMNI_TIMEOUT_SECONDS=600
EOF

# Apply Gradio 6 compatibility patches
echo "Applying Gradio 6 compatibility patches..."
# Fix Chatbot args
sed -i "s/type=\"messages\",//g" biomni/agent/a1.py
sed -i "s/show_copy_button=True,//g" biomni/agent/a1.py
sed -i "s/show_share_button=True,//g" biomni/agent/a1.py
# Fix launch args
sed -i "s/demo\.launch(share=share, server_name=server_name)/demo.launch(share=share, server_name=server_name, strict_cors=False, ssr_mode=False)/g" biomni/agent/a1.py

# Add Ollama/Custom model XML tag hint
python3 -c "
import re
path = 'biomni/agent/a1.py'
with open(path) as f:
    content = f.read()
if 'IMPORTANT: You MUST use XML tags' not in content:
    old = '''system_prompt += \"\\\\n\\\\nIMPORTANT FOR GPT MODELS: You MUST use XML tags <execute> or <solution> in EVERY response. Do not use markdown code blocks (\\\`\\\`\\\`) - use <execute> tags instead.\"'''
    new = old + '''
            # Also add hint for non-Anthropic/non-GPT models (Ollama, Custom vLLM, etc.)
            if \"ollama\" in str(type(self.llm)).lower() or \"custom\" in str(getattr(self, \"source\", \"\")).lower():
                system_prompt += \"\\\\n\\\\nIMPORTANT: You MUST use XML tags <execute> or <solution> in EVERY response. Do not use markdown code blocks (\\\`\\\`\\\`) - use <execute> tags instead. For simple questions that don\\'t need code, wrap your answer in <solution>your answer</solution>.\"'''
    if old in content:
        content = content.replace(old, new)
        with open(path, 'w') as f:
            f.write(content)
        print('Patched agent for Custom/Ollama XML hints')
    else:
        print('Could not find patch target, may need manual patching')
else:
    print('Already patched')
" 2>/dev/null || echo "Auto-patch skipped, may need manual patching from the Mac version"

# Create launch script
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null)
cat > launch_biomni.sh <<'LAUNCH_EOF'
#!/bin/bash
eval "$(${HOME}/miniforge3/bin/conda shell.bash hook)"
conda activate biomni_e1
cd $HOME/Biomni

python -u -c "
from biomni.agent import A1

agent = A1(
    path='./data',
    llm='meta-llama/Llama-3.3-70B-Instruct',
    source='Custom',
    base_url='http://localhost:8000/v1',
    api_key='EMPTY',
    expected_data_lake_files=[],
    use_tool_retriever=False,
)
agent.launch_gradio_demo()
"
LAUNCH_EOF
chmod +x launch_biomni.sh

echo ""
echo "=== Phase 5 Complete ==="
echo ""
echo "Launch Biomni:"
echo "  bash ~/Biomni/launch_biomni.sh"
echo ""
echo "Access from anywhere via Tailscale:"
echo "  http://${TAILSCALE_IP}:${BIOMNI_PORT}"
echo ""
echo "=== ALL PHASES COMPLETE ==="
echo ""
echo "Summary:"
echo "  Spark A Tailscale: ${TAILSCALE_IP}"
echo "  Spark B Tailscale: $(ssh ${NODE2_QSFP_IP} 'tailscale ip -4' 2>/dev/null || echo '<check on Spark B>')"
echo "  vLLM API:          http://${TAILSCALE_IP}:${VLLM_PORT}/v1"
echo "  Biomni UI:         http://${TAILSCALE_IP}:${BIOMNI_PORT}"
echo "  Model:             ${MODEL} (TP=2 across both Sparks)"
;;

##############################################################################
*)
echo "DGX Spark Dual-Node Setup for Biomni + vLLM"
echo ""
echo "Usage: bash dgx-spark-setup.sh <phase>"
echo ""
echo "Phases (run in order):"
echo "  phase1         Base setup + Tailscale (run on BOTH Sparks)"
echo "  phase2-node1   QSFP network for Spark A"
echo "  phase2-node2   QSFP network for Spark B"
echo "  phase3-head    vLLM cluster head (Spark A)"
echo "  phase3-worker  vLLM cluster worker (Spark B)"
echo "  phase4         Download model & launch vLLM"
echo "  phase5         Install Biomni (Spark A)"
;;

esac
