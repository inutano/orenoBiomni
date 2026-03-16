#!/bin/bash
set -e

# Activate conda environment
eval "$(conda shell.bash hook)"
conda activate biomni_e1

cd /app/Biomni

# Defaults
MODEL="${BIOMNI_LLM:-qwen3.5:35b-a3b-q8_0}"
SOURCE="${BIOMNI_SOURCE:-Ollama}"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"

# Wait for Ollama to be ready
if [ "$SOURCE" = "Ollama" ]; then
    echo "Waiting for Ollama at ${OLLAMA_URL}..."
    until curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; do
        sleep 2
    done
    echo "Ollama is ready."

    # Pull model if not already available
    MODEL_EXISTS=$(curl -sf "${OLLAMA_URL}/api/tags" | python3 -c "
import sys, json
tags = json.load(sys.stdin).get('models', [])
print('yes' if any('${MODEL}' in m.get('name','') for m in tags) else 'no')
" 2>/dev/null || echo "no")

    if [ "$MODEL_EXISTS" = "no" ]; then
        echo "Pulling model ${MODEL}..."
        curl -sf "${OLLAMA_URL}/api/pull" -d "{\"name\":\"${MODEL}\"}" | while read -r line; do
            STATUS=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
            [ -n "$STATUS" ] && echo "  $STATUS"
        done
    fi

    # Pre-warm model
    echo "Pre-warming model..."
    curl -sf "${OLLAMA_URL}/api/generate" -d "{\"model\":\"${MODEL}\",\"prompt\":\"Hi\",\"stream\":false,\"options\":{\"num_predict\":1}}" > /dev/null 2>&1
    echo "Model ready."
fi

# Build launch arguments
LAUNCH_ARGS=""
if [ "$SOURCE" = "Ollama" ]; then
    LAUNCH_ARGS="source='Ollama'"
elif [ "$SOURCE" = "Custom" ]; then
    LAUNCH_ARGS="source='Custom', base_url='${BIOMNI_CUSTOM_BASE_URL}', api_key='${BIOMNI_CUSTOM_API_KEY}'"
else
    LAUNCH_ARGS="source='${SOURCE}'"
fi

echo "Launching orenoBiomni (model=${MODEL}, source=${SOURCE})"

exec python -u -c "
import os
os.environ['OLLAMA_HOST'] = '${OLLAMA_URL}'

from biomni.agent import A1

agent = A1(
    path='./data',
    llm='${MODEL}',
    ${LAUNCH_ARGS},
    expected_data_lake_files=[],
    use_tool_retriever=False,
)
agent.launch_gradio_demo()
"
