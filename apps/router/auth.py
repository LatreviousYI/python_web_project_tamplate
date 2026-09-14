"""
鉴权路由

fastgo 单点登录：
- GET /auth/login-url   获取登录地址（前端重定向跳转）
- POST /auth/login      用 ticket 换取用户信息 + 本地 JWT
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from apps.service import auth as auth_service
from common.db import get_session
from utils import fast_go
from utils.response_utils import ApiResponse

router = APIRouter(prefix="/auth")


@router.get("/login-url")
async def get_sso_login_url(redirect_url: str = Query(...)) -> ApiResponse:
    login_url = fast_go.get_login_url(redirect_url, False)
    return ApiResponse(data={"login_url": login_url})


class LoginPayload(BaseModel):
    ticket: str


@router.post("/login")
async def login(payload: LoginPayload, session=Depends(get_session)) -> ApiResponse:
    result = await auth_service.fastgo_login(session, payload.ticket)
    return ApiResponse(data=result)
