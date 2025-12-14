
"""
使用 asyncpg 检查 DATABASE_URL 是否可连，并打印版本信息。
从环境变量 DATABASE_URL 读取连接串（与后端一致），不在代码中硬编码密码。

运行示例：
  uv run python backend/utils/test_db.py
"""

import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse

import asyncpg


def load_env_database_url() -> str | None:
    """从环境变量或根目录 .env 获取 DATABASE_URL。"""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    # 尝试读取项目根的 .env（脚本位于 backend/utils/）
    candidates = [
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for path in candidates:
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip().startswith("DATABASE_URL"):
                    _, _, val = line.partition("=")
                    return val.strip().strip('"').strip("'")
    return None


RAW_DATABASE_URL = load_env_database_url() or "postgresql://user:password@localhost:5432/fireworks_db"


def normalize_dsn(url: str) -> str:
    """asyncpg 仅接受 postgresql/postgres scheme，去掉 +asyncpg 等后缀。"""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


async def main():
    dsn = normalize_dsn(RAW_DATABASE_URL)
    parsed = urlparse(dsn)
    host = parsed.hostname or "unknown"
    port = parsed.port or "?"
    print(f"正在尝试连接 {host}:{port} ...")
    try:
        conn = await asyncpg.connect(dsn)
        version = await conn.fetchval("select version();")
        print("✅ 连接成功")
        print(f"数据库版本: {version}")
        await conn.close()
    except Exception as exc:
        print("❌ 连接失败")
        print(f"错误信息: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
