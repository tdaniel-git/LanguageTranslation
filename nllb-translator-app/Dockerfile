# NLLB Translator — containerized (CPU build).
FROM python:3.11-slim

# System deps occasionally needed by tokenizers/torch wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY backend ./backend
COPY frontend ./frontend

# Hugging Face cache location (mount a volume here to persist the model).
ENV HF_HOME=/app/.hf_cache
ENV PORT=8000
EXPOSE 8000

# Model downloads on first request (~2.5GB). Mount -v hf_cache:/app/.hf_cache to reuse.
WORKDIR /app/backend
CMD ["python", "app.py"]
