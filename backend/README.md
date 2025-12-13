# 烟花后台后端使用说明

本说明针对后端 FastAPI 服务的使用与启动方式，开发设计文档请见 `docs/plan.md`。

## 运行要求
- Python 3.14+
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
pip install fastapi uvicorn[standard] pydantic python-multipart
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
docker compose up --build
```
默认端口：后端 8000，Postgres 5432（如不需要外露，可移除端口映射）。

## 主要接口（基于当前内存 mock 数据）
- `POST /api/auth/login`
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
- `DATABASE_URL`：预留给未来接入 PostgreSQL（Compose 中已提供示例）。当前代码使用内存数据，可为空。

## 注意
- 当前后端为内存 mock，用于前端联调与接口对齐；接入数据库时，请替换 `app/services/mock_store.py` 为真实仓储实现。
- 宿主机已有 Nginx 负责 SSL/反代时，后端仅需监听内网端口（如 8000），由 Nginx 转发。***
