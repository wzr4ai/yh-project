FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# Install build/runtime deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (no lock yet, keep minimal)
RUN python -m pip install --upgrade pip \
    && pip install fastapi uvicorn[standard] pydantic python-multipart python-jose[cryptography] sqlalchemy asyncpg httpx

COPY app ${APP_HOME}/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000","--reload"]
