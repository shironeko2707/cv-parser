#!/bin/bash
# Quick setup script for CV Parser Pipeline (AI-powered)
set -e

echo "=== CV Parser Setup ==="

# Clear old bytecode cache
echo "Clearing __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Install Python dependencies
pip install -r requirements.txt

echo ""
echo "=== Setup complete! ==="
echo ""
echo "=== LLM Server Setup ==="
echo ""
echo "Option 1: Ollama (recommended)"
echo "  ollama pull gemma4:e2b"
echo "  ollama serve"
echo ""
echo "Option 2: llama.cpp"
echo "  llama-server -m gemma4-e2b.gguf --port 8080"
echo "  export LLM_BASE_URL=http://localhost:8080/v1"
echo "  export LLM_MODEL=gemma4-e2b"
echo ""
echo "=== Usage ==="
echo ""
echo "  # Web UI"
echo "  python app.py                    # -> http://localhost:5005"
echo ""
echo "  # CLI - single file"
echo "  python main.py resume.pdf -o output.json"
echo ""
echo "  # CLI - batch"
echo "  python main.py ./cv_folder/ --output ./output/"
echo ""
echo "  # Environment variables:"
echo "  LLM_BASE_URL   default: http://localhost:11434/v1"
echo "  LLM_MODEL      default: gemma4:e2b"
echo "  LLM_TIMEOUT    default: 120 (seconds)"
