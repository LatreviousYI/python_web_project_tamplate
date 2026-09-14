"""
JWT 工具模块

提供 token 的生成与校验，以及 FastAPI 鉴权依赖。
当前为 SSO-ready 占位：假定 SSO 已发放 JWT，token 中携带 user_id。
"""

from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from configs import settings
from utils import response_utils
from utils.log_util import logger


class HTTPBearerRaise401(HTTPBearer):
    """从 Authorization 头解析 Bearer token，缺失/非法时抛 401。"""

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
            else:
                return None
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )
            else:
                return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


def generate_token(data: dict, expiration_delta: Optional[timedelta] = None):
    """生成 JWT。data 中通常包含 user_id。"""
    token_data = data.copy()
    if not expiration_delta:
        expiration_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expiration_time = datetime.now() + expiration_delta
    token_data.update({"exp": expiration_time.timestamp()})
    encoded_token = jwt.encode(token_data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_token


def get_uid_from_jwt(token: str):
    """从 JWT 解出 user_id。"""
    decoded_payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    return decoded_payload.get("user_id")


def decode_token_get_info(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearerRaise401()),
) -> dict:
    """解析并校验 token，返回其 payload。"""
    token = credentials.credentials
    try:
        decoded_payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except (ExpiredSignatureError, InvalidTokenError) as e:
        logger.exception(f"token verification error. {e}")
        response_utils.invalid_token()
    except Exception as e:
        logger.exception(f"token verification error. {e}")
        response_utils.invalid_token()
    if not decoded_payload:
        response_utils.invalid_token()
    return decoded_payload


def verify_token(token_info: dict = Depends(decode_token_get_info)) -> int:
    """鉴权依赖：返回当前用户主键 id（int）。"""
    return token_info.get("user_id")


def decode_token_get_info_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearerRaise401(auto_error=False)),
) -> Optional[dict]:
    """解析并校验 token（可选鉴权）：未携带 / 非法 token 时返回 None，不抛异常。"""
    if credentials is None:
        return None
    token = credentials.credentials
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except (ExpiredSignatureError, InvalidTokenError):
        return None


def verify_token_optional(token_info: Optional[dict] = Depends(decode_token_get_info_optional)) -> Optional[int]:
    """可选鉴权依赖：已登录返回用户主键 id（int），未登录 / 非法 token 返回 None。"""
    if token_info is None:
        return None
    return token_info.get("user_id")
