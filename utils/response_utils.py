"""
统一响应模型

接口响应统一用 pydantic 模型表达，路由直接返回模型实例，
由 FastAPI 自动序列化（嵌套 pydantic 模型、datetime 等类型也会正确输出）。

统一结构：{ code, message, data }
- code: 200 成功；其它为业务错误码
- message: 提示信息
- data: 业务数据（可为 None / 对象 / 分页结构 PageResult）
"""

from typing import Any, NoReturn

from fastapi import HTTPException, status
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一响应包裹。"""

    code: int = 200
    message: str = "success"
    data: Any = None


class PageResult(BaseModel):
    """分页结果。"""

    totals: int
    data: list


# -- 以下为异常辅助（抛出 HTTPException，用于 401/403/400 等，非响应构建）--


def invalid_params() -> NoReturn:
    """参数无效响应（400）"""
    server_error(status.HTTP_400_BAD_REQUEST, "Invalid parameter")


def abort(code, message) -> NoReturn:
    """抛出指定状态码的 HTTP 异常"""
    raise HTTPException(status_code=code, detail=message)


def server_error(code, detail, headers=None) -> NoReturn:
    """抛出指定状态码和详情的 HTTP 异常"""
    raise HTTPException(status_code=code, detail=detail, headers=headers)


def invalid_token() -> NoReturn:
    """令牌无效响应（401），返回 WWW-Authenticate 头"""
    server_error(status.HTTP_401_UNAUTHORIZED, "Invalid token", {"WWW-Authenticate": "Bearer"})


def invalid_permission(detail="没有权限") -> NoReturn:
    """权限不足响应（403）"""
    server_error(status.HTTP_403_FORBIDDEN, detail)
