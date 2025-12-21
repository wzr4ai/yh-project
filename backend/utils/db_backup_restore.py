"""
PostgreSQL 备份/恢复脚本（基于 pg_dump / psql）。

运行：
  cd backend
  set -a; source .env; set +a
  uv run python utils/db_backup_restore.py backup
  uv run python utils/db_backup_restore.py restore --file /path/to/backup.sql

可选参数：
  --db-url        直接指定 DATABASE_URL（优先于 .env/环境变量）
  --output-dir    备份输出目录（默认：backend/files/db_backups）
  --file          指定备份/恢复文件路径
  --reset-schema  恢复前重建 public schema（危险，默认关闭）
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


def _load_env_file_if_present(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, _, val = raw.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def ensure_env_loaded() -> None:
    env_candidates = [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for env_path in env_candidates:
        _load_env_file_if_present(env_path)


def get_database_url() -> str | None:
    ensure_env_loaded()
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url
    return None


def build_pg_env(db_url: str) -> dict[str, str]:
    parsed = urlparse(db_url)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError("DATABASE_URL must be postgresql://")
    env = os.environ.copy()
    if parsed.hostname:
        env["PGHOST"] = parsed.hostname
    if parsed.port:
        env["PGPORT"] = str(parsed.port)
    if parsed.username:
        env["PGUSER"] = unquote(parsed.username)
    if parsed.password:
        env["PGPASSWORD"] = unquote(parsed.password)
    dbname = (parsed.path or "").lstrip("/")
    if dbname:
        env["PGDATABASE"] = dbname
    return env


def require_cmd(cmd: str) -> None:
    if not shutil.which(cmd):
        raise RuntimeError(f"缺少命令：{cmd}（请安装 postgresql-client）")


def run_cmd(cmd: list[str], env: dict[str, str], capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, env=env, check=True, text=True, capture_output=capture)


def do_backup(db_url: str, output_dir: Path, file_path: Path | None) -> Path:
    require_cmd("pg_dump")
    output_dir.mkdir(parents=True, exist_ok=True)
    if file_path:
        target = file_path
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = output_dir / f"backup_{ts}.sql"
    env = build_pg_env(db_url)
    cmd = [
        "pg_dump",
        "--format=plain",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(target),
    ]
    run_cmd(cmd, env)
    return target


def do_restore(db_url: str, file_path: Path, reset_schema: bool) -> None:
    require_cmd("psql")
    if not file_path.exists():
        raise FileNotFoundError(f"备份文件不存在：{file_path}")
    env = build_pg_env(db_url)
    if reset_schema:
        cmd_reset = [
            "psql",
            "--set",
            "ON_ERROR_STOP=on",
            "-c",
            "DROP SCHEMA public CASCADE; CREATE SCHEMA public;",
        ]
        run_cmd(cmd_reset, env)
    cmd = ["psql", "--set", "ON_ERROR_STOP=on", "--file", str(file_path)]
    try:
        run_cmd(cmd, env, capture=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").lower()
        if "already exists" in stderr or "relation" in stderr:
            print("恢复失败：目标库已有表/对象。可用 --reset-schema 先清空 schema，或恢复到空库。")
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PostgreSQL 备份/恢复")
    sub = parser.add_subparsers(dest="action", required=True)

    p_backup = sub.add_parser("backup", help="生成备份")
    p_backup.add_argument("--db-url", default=None, help="覆盖 DATABASE_URL")
    p_backup.add_argument("--output-dir", default=None, help="备份输出目录")
    p_backup.add_argument("--file", default=None, help="备份文件路径（.sql）")

    p_restore = sub.add_parser("restore", help="恢复备份")
    p_restore.add_argument("--db-url", default=None, help="覆盖 DATABASE_URL")
    p_restore.add_argument("--file", required=True, help="备份文件路径（.sql）")
    p_restore.add_argument("--reset-schema", action="store_true", help="恢复前重建 public schema（危险）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_url = args.db_url or get_database_url()
    if not db_url:
        raise RuntimeError("缺少 DATABASE_URL，请在环境变量或 .env 中配置。")

    if args.action == "backup":
        output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parent.parent / "files" / "db_backups"
        file_path = Path(args.file) if args.file else None
        target = do_backup(db_url, output_dir, file_path)
        print(f"备份完成：{target}")
        return

    if args.action == "restore":
        do_restore(db_url, Path(args.file), reset_schema=args.reset_schema)
        print("恢复完成。")


if __name__ == "__main__":
    main()
