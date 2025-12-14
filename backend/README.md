# 烟花后台后端使用说明

本说明针对后端 FastAPI 服务的使用与启动方式，开发设计文档请见 `docs/plan.md`。

## 运行要求
- Python 3.11+
- uv（推荐）或 pip
- Docker / Docker Compose（可选，用于容器化）

## 本地运行（uv）
```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 本地运行（pip）
```bash
cd backend
python -m pip install --upgrade pip
pip install fastapi uvicorn[standard] pydantic python-multipart python-jose[cryptography] sqlalchemy asyncpg
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker 构建与运行
### 单服务镜像
```bash
cd backend
docker build -t yh-backend:latest .
docker run -p 8000:8000 yh-backend:latest
```

### Compose（含 Postgres）
根目录已有 `docker-compose.yml`：
```bash
# 复制示例配置
cp .env.example .env
# 启动
docker compose up --build
```
默认端口：后端 8000，Postgres 5432（如不需要外露，可移除端口映射）。Postgres 18 使用卷挂载到 `/var/lib/postgresql`（见 compose），升级旧卷需按官方指引 pg_upgrade 或清理旧卷后重建。

## 主要接口（DB 版）
- `POST /api/auth/weapp`：微信 code 换 JWT（不存在则自动注册为店员，落库）
- `GET /api/me`：通过 Bearer Token 获取当前用户
- `GET /api/price/calculate/{product_id}`
- `POST /api/products`
- `PUT /api/categories/{id}`
- `POST /api/import/products`（占位，模拟任务）
- `GET /api/import/{job_id}`
- `POST /api/sales`
- `POST /api/inventory/adjust`
- `GET /api/inventory/logs`
- `GET /api/purchase-orders`
- `POST /api/purchase-orders`
- `PUT /api/purchase-orders/{po_id}/receive`
- `GET /api/dashboard/realtime`
- `GET /api/dashboard/inventory_value`
- `GET /api/dashboard/performance`

## 环境变量
- `DATABASE_URL`：PostgreSQL 连接串。若使用非 async 写法，可写成 `postgresql://...`，程序会自动替换成 `postgresql+asyncpg://...`。
- `SECRET_KEY`：JWT 密钥；目前代码在 `app/services/auth.py` 内置默认值，生产请改为环境变量。
- `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`：Compose 下的数据库配置（见 `.env.example`）。
- `WECHAT_APPID` / `WECHAT_SECRET`：微信小程序登录所需。若未配置，登录接口会回退为本地 mock openid（仅开发用途）。

## 注意
- 已切换为 Postgres 持久化，启动时自动建表并初始化默认全局系数与默认仓。
- 宿主机已有 Nginx 负责 SSL/反代时，后端仅需监听内网端口（如 8000），由 Nginx 转发。***

## 轻量迁移脚本
- 针对当前模型新增的列/表，可运行：
```bash
cd backend
set -a; source .env; set +a
uv run python backend/utils/schema_migrate.py
```
该脚本会：
- 创建缺失表（基于模型 metadata）
- 补充 `product.retail_multiplier`、`product.pack_price_ref` 列
- 创建 `product_category` 关联表

复杂结构变更请使用 Alembic 等正式迁移工具。***
