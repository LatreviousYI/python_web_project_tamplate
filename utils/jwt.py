import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional

import bcrypt  # python -m pip install bcrypt
import jwt  # python -m pip install pyjwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param

from vrm.tomo.configs import settings
from vrm.tomo.exts import promotes
from vrm.tomo.utils import response_utils
from vrm.tomo.utils.log_util import logger
from vrm.tomo.utils.response_utils import abort


class HTTPBearerRaise401(HTTPBearer):
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


def set_password(password):
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed_password.decode("utf-8")


def validate_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def generate_token(data: dict, expiration_delta=None):
    token_data = data.copy()  # data = {'id': 3}
    if not expiration_delta:
        expiration_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expiration_time = datetime.now() + expiration_delta
    token_data.update({"exp": expiration_time.timestamp()})
    encoded_token = jwt.encode(token_data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_token


def get_uid_from_jwt(token: str):
    decoded_payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    user_id = decoded_payload.get("id")
    return user_id


# def invalid_token():
#     invalid_request(status.HTTP_401_UNAUTHORIZED, "Invalid token", {"WWW-Authenticate": "Bearer"})


# def invalid_permission(detail="没有权限"):
#     invalid_request(status.HTTP_403_FORBIDDEN, detail)


# def invalid_request(code, detail, headers=None):
#     raise HTTPException(status_code=code, detail=detail, headers=headers)


def decode_token_get_info(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearerRaise401()),
):
    token = credentials.credentials
    try:
        decoded_payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except (ExpiredSignatureError, InvalidTokenError) as e:
        logger.exception(f"token verification error. {e}")
        response_utils.invalid_token()
    except (Exception,) as e:
        logger.exception(f"token verification error. {e}")
        response_utils.invalid_token()
    if not decoded_payload:
        response_utils.invalid_token()
    return decoded_payload


# 依赖函数 身份验证
def verify_token(token_info: dict = Depends(decode_token_get_info)):
    return token_info.get("id")


def verify_fast_token(token_info: dict = Depends(decode_token_get_info)):
    return token_info.get("fast_token")


def get_app_secret(data_list, target_app_key):
    for item in data_list:
        if item["app_key"] == target_app_key:
            return item["app_secret"]
    return None


def generate_signature(params, app_secret):
    sorted_params = {k: v for k, v in sorted(params.items()) if v is not None}
    strings = "&".join(f"{k}={v}" for k, v in sorted_params.items())
    sign_temp = f"{strings}{app_secret}"
    md5_hash = hashlib.md5(sign_temp.encode("utf-8")).hexdigest().upper()
    return md5_hash


def get_headers_with_signature(signature):
    headers = {"Content-Type": "application/json", "signature": signature}
    return headers


def validate_request(headers, body, time_limit: int):
    received_signature = headers.get("signature")
    if not received_signature:
        abort(400, "missing signature")
    appkey = body.get("appkey")
    timestamp = body.get("timestamp")
    if not appkey or not timestamp:
        abort(400, "missing required parameters")
    current_time = int(time.time() * 1000)  # 毫秒
    if abs(current_time - int(timestamp)) > time_limit:
        abort(400, "timestamp is too old or too new")
    api_keys = promotes.promotes["api_keys"]  # list
    app_secret = get_app_secret(api_keys, appkey)
    if not app_secret:
        abort(403, "invalid appkey")
    params = {"appkey": appkey, "timestamp": timestamp}
    server_signature = generate_signature(params, app_secret)
    if server_signature != received_signature:
        abort(403, "invalid signature")
    return True
