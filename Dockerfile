# BillBhasha — single free-tier container (backend + frontend).
# Models are baked in at build time so cold boots stay fast.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WEB_CONCURRENCY=1 \
    N_THREADS=1 \
    N_CTX=1024

# System deps: OCR engine + Hindi+English+Bengali data + audio conversion.
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-ben \
      ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Light deps first (cached layer), optional ML second (commented by default).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---- optional: fully offline on-box AI (uncomment to enable) ----
# COPY requirements-ml.txt scripts/download_models.sh ./scripts/
# RUN pip install --no-cache-dir -r requirements-ml.txt \
#  && bash scripts/download_models.sh

COPY src ./src
COPY data ./data

EXPOSE 8000

# Single worker = the RAM promise (512MB free tier).
CMD ["sh", "-c", "uvicorn src.backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
