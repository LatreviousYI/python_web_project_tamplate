"""
鉴权路由

fastgo 单点登录：
- GET /auth/login-url   获取登录地址（前端重定向跳转）
- POST /auth/login      用 ticket 换取用户信息 + 本地 JWT
- POST /auth/logout     退出登录（注销 SSO 会话）
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from apps import dependencies
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


@router.post("/logout")
async def logout(token_info: dict = Depends(dependencies.get_current_token_info)) -> ApiResponse:
    """退出登录：注销 SSO 的 fast_token（本地 JWT 由客户端丢弃）。"""
    fast_token = token_info.get("fast_token")
    if fast_token:
        await auth_service.fastgo_logout(fast_token)
    return ApiResponse()
