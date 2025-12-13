import hashlib
import os
import time
from typing import Optional

import httpx
from jose import JWTError, jwt

from app.models.schemas import Role, User

SECRET_KEY = os.getenv("SECRET_KEY", "replace-me-with-env-secret")
WECHAT_APPID = os.getenv("WECHAT_APPID")
WECHAT_SECRET = os.getenv("WECHAT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 12  # 12h


async def weapp_code_to_openid(code: str) -> str:
    """
    微信 code 换 openid.
    若未配置 appid/secret，则抛出 ValueError。
    """
    if not WECHAT_APPID or not WECHAT_SECRET:
        raise ValueError("WECHAT_APPID/WECHAT_SECRET not configured")
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": WECHAT_APPID,
        "secret": WECHAT_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    if data.get("errcode"):
        raise ValueError(f"wechat auth error: {data.get('errmsg')}")
    openid = data.get("openid")
    if not openid:
        raise ValueError("wechat auth error: openid missing")
    return openid


def make_openid_from_code(code: str) -> str:
    """本地/缺省配置下的模拟 openid 生成."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def create_access_token(user: User) -> str:
    now = int(time.time())
    payload = {
        "sub": user.id,
        "role": user.role,
        "username": user.username,
        "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS,
        "iat": now,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def role_from_token(token: str) -> Optional[Role]:
    data = decode_token(token)
    if not data:
        return None
    return data.get("role")  # type: ignore
