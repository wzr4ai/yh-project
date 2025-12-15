FROM registry.cn-hangzhou.aliyuncs.com/google_containers/python:3.14-slim AS base

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

# Install project dependencies (use pyproject)
COPY pyproject.toml ${APP_HOME}/
RUN python -m pip install --upgrade pip \
    && pip install .

# Copy source
COPY app ${APP_HOME}/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
