from fastapi import Depends, Header, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.schemas import User
from app.services import auth, logic


async def get_current_user(
    authorization: str | None = Header(default=None), session: AsyncSession = Depends(get_session)
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    payload = auth.decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    user = await logic.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
