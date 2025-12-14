set -a; source .env; set +a
uv run uvicorn app.main:app --port 8000 --reload