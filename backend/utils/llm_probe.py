"""
Quick smoke test for the LLM bridge.

Usage:
  uv run python backend/utils/llm_probe.py "你好，给我一个简短回复" --protocol gemini --tier low

Loads LLM_* variables from environment (or falls back to .env) and sends a one-shot prompt.
"""

import argparse
import asyncio
import os
from pathlib import Path

from app.models.schemas import LLMMessage
from app.services.llm import LLMService, LLMServiceError


def preload_env():
    if os.getenv("LLM_BASE_URL"):
        return
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith("LLM_") and not os.getenv(key):
            os.environ[key] = val.strip().strip('"').strip("'")


async def main():
    parser = argparse.ArgumentParser(description="LLM bridge quick test")
    parser.add_argument("prompt", nargs="?", default="ping", help="User message to send to the LLM")
    parser.add_argument("--protocol", choices=["gemini", "openai", "open"], default=None, help="Target protocol")
    parser.add_argument("--tier", choices=["low", "mid", "high"], default="low", help="Model tier to use")
    parser.add_argument("--model", default=None, help="Override model name (otherwise tier mapping is used)")
    args = parser.parse_args()

    preload_env()
    service = LLMService()
    message = LLMMessage(role="user", content=args.prompt)
    try:
        resp = await service.chat(
            [message],
            model_tier=args.tier,  # type: ignore[arg-type]
            protocol=args.protocol,  # type: ignore[arg-type]
            model=args.model,
        )
    except (ValueError, LLMServiceError) as exc:
        print(f"LLM call failed: {exc}")
        return

    print(f"protocol={resp.protocol} model={resp.model} finish_reason={resp.finish_reason}")
    if resp.raw_usage:
        print(f"usage={resp.raw_usage}")
    print("reply:")
    print(resp.content)


if __name__ == "__main__":
    asyncio.run(main())
