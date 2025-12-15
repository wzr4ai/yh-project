# 建议确认一下 python 版本，3.14 目前可能还是开发版，如果是 3.13 或 3.12 请自行修改
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    APP_HOME=/app \
    # ✅ 新增：配置 pip 使用腾讯云镜像源 (公网/内网通用)
    PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple

WORKDIR ${APP_HOME}

# ✅ 优化重点：替换系统源为腾讯云内网源
# 1. 这里的 sed 命令会将 debian.org 替换为腾讯云内网源 (mirrors.tencentyun.com)
# 2. 只有在腾讯云服务器上构建时，才能使用 tencentyun.com (速度最快，内网流量)
# 3. 如果你在本地电脑构建，请将 tencentyun.com 改为 cloud.tencent.com
RUN sed -i 's/deb.debian.org/mirrors.tencentyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/deb.debian.org/mirrors.tencentyun.com/g' /etc/apt/sources.list 2>/dev/null || true \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install project dependencies
COPY pyproject.toml ${APP_HOME}/
# pip install 会自动读取上面的 PIP_INDEX_URL 环境变量
RUN python -m pip install --upgrade pip \
    && pip install .

# Copy source
COPY app ${APP_HOME}/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]