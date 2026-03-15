#!/bin/bash
set -e

##############################################################################
# orenoBiomni Launch Script
# Launches Biomni with Ollama backend
#
# Usage:
#   bash launch.sh [--model MODEL] [--biomni-dir DIR] [--port PORT]
##############################################################################

MODEL="${MODEL:-qwen3.5:35b-a3b-q8_0}"
BIOMNI_DIR="${BIOMNI_DIR:-$(pwd)/Biomni}"
PORT="${PORT:-7860}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --model) MODEL="$2"; shift 2 ;;
        --biomni-dir) BIOMNI_DIR="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Activate conda
if [ -f "$HOME/miniforge3/bin/activate" ]; then
    source "$HOME/miniforge3/bin/activate"
elif command -v conda &>/dev/null; then
    eval "$(conda shell.bash hook)"
fi
conda activate biomni_e1

cd "$BIOMNI_DIR"

echo "Launching orenoBiomni"
echo "  Model: $MODEL"
echo "  Port:  $PORT"
echo "  Dir:   $BIOMNI_DIR"
echo ""

python -u -c "
from biomni.agent import A1

agent = A1(
    path='./data',
    llm='${MODEL}',
    source='Ollama',
    expected_data_lake_files=[],
    use_tool_retriever=False,
)
agent.launch_gradio_demo()
"
