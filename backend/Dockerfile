# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 -- build the venv and bake the embedding model into the image.
#
# The model is downloaded here, not at runtime: Railway containers sleep on the
# free tier, and a cold start that also has to fetch 130MB from HuggingFace is
# the difference between a 3-second wake and a 40-second one.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    HF_HOME=/opt/hf-cache

RUN pip install --no-cache-dir uv

WORKDIR /build
COPY pyproject.toml ./

RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv PATH="/opt/venv/bin:$PATH"

# CPU-only torch first, from the PyTorch CPU index. The default PyPI wheel pulls
# the whole CUDA stack (~2.5GB) that a Railway container can never use.
RUN uv pip install --no-cache torch --index-url https://download.pytorch.org/whl/cpu

RUN uv pip install --no-cache -r pyproject.toml

# Warm the HuggingFace cache that the runtime stage copies.
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('BAAI/bge-small-en-v1.5')"


# ---------------------------------------------------------------------------
# Stage 2 -- runtime.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/opt/hf-cache \
    PORT=8000

# libgomp is torch's OpenMP runtime; the slim image does not ship it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/hf-cache /opt/hf-cache

WORKDIR /app
COPY app ./app

RUN useradd --create-home --uid 10001 vacancyscore \
    && chown -R vacancyscore:vacancyscore /app
USER vacancyscore

EXPOSE 8000

# Railway injects PORT; the default keeps `docker run -p 8000:8000` working.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
