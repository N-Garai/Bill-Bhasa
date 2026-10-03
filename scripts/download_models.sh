#!/usr/bin/env bash
# Downloads open-weight models + voices into /models (baked into the image).
# All free, all open licences. Run inside docker build only.
set -euo pipefail
mkdir -p /models /usr/share/tesseract-ocr/5/tessdata

echo "-> LLM: SmolLM2-360M-Instruct Q4_K_M (Apache-2.0)"
curl -L -o /models/smollm2-360m-instruct-q4_k_m.gguf \
  "https://huggingface.co/HuggingFaceTB/smollm2-360m-instruct/resolve/main/smollm2-360m-instruct-q4_k_m.gguf?download=true" || true

echo "-> Piper Hindi voice (MIT)"
curl -L -o /models/hi_IN-pratham-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx?download=true" || true
curl -L -o /models/hi_IN-pratham-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx.json?download=true" || true

echo "-> Piper binary"
PIPER_VER="1.2.0"
curl -L -o /tmp/piper.tar.gz \
  "https://github.com/rhasspy/piper/releases/download/${PIPER_VER}/piper_linux_x86_64.tar.gz" || true
tar -xzf /tmp/piper.tar.gz -C /usr/local/bin --strip-components=1 2>/dev/null || true

echo "done. ls /models:"
ls -lh /models || true
