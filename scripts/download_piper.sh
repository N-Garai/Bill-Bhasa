#!/usr/bin/env bash
# Bakes the Piper Hindi voice into the image (MIT licence, ~90MB total).
# Fail-soft by design: if the network/assets move, the build still succeeds
# and the app falls back to the phone's own voice.
set -uo pipefail
mkdir -p /models

echo "-> Piper binary"
if curl -fsSL -o /tmp/piper.tar.gz \
  "https://github.com/rhasspy/piper/releases/download/1.2.0/piper_linux_x86_64.tar.gz"; then
  mkdir -p /tmp/piper && tar -xzf /tmp/piper.tar.gz -C /tmp/piper || true
  BIN=$(find /tmp/piper -name piper -type f | head -1 || true)
  if [ -n "${BIN}" ]; then cp "${BIN}" /usr/local/bin/piper && chmod +x /usr/local/bin/piper; fi
fi

echo "-> Hindi voice hi_IN-pratham-medium"
curl -fsSL -o /models/hi_IN-pratham-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx?download=true" || true
curl -fsSL -o /models/hi_IN-pratham-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx.json?download=true" || true

echo "-> Bengali voice bn_BD-google-medium"
curl -fsSL -o /models/bn_BD-google-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/bn/bn_BD/google/medium/bn_BD-google-medium.onnx?download=true" || true
curl -fsSL -o /models/bn_BD-google-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/bn/bn_BD/google/medium/bn_BD-google-medium.onnx.json?download=true" || true

echo "done:"
which piper || echo "(no piper binary — browser voice fallback stays active)"
ls -lh /models || true
