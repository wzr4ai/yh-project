from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db import get_session
from app.models import schemas
from app.services import auth, logic

router = APIRouter()


@router.post("/auth/weapp", response_model=schemas.LoginResponse)
async def login_weapp(payload: schemas.WeappLoginRequest, session: AsyncSession = Depends(get_session)):
    try:
        openid = await auth.weapp_code_to_openid(payload.code)
    except ValueError:
        openid = auth.make_openid_from_code(payload.code)
    user = await logic.get_or_create_user_by_openid(session, openid, payload.nickname)
    await session.commit()
    token = auth.create_access_token(user)
    return schemas.LoginResponse(token=token, username=user.username, role=user.role)


@router.get("/me", response_model=schemas.UserOut)
async def me(current_user=Depends(deps.get_current_user)):
    return current_user
