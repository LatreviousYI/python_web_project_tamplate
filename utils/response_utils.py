"""
响应工具模块

提供统一的API响应格式，包括成功响应、错误响应、分页结构等
"""

import json
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from vrm.tomo.utils import tools


def invalid_params():
    """参数无效响应（400）"""
    server_error(status.HTTP_400_BAD_REQUEST, "Invalid parameter")


def abort(code, message):
    """抛出指定状态码的HTTP异常"""
    raise HTTPException(status_code=code, detail=message)


def server_error(code, detail, headers=None):
    """抛出指定状态码和详情的HTTP异常"""
    raise HTTPException(status_code=code, detail=detail, headers=headers)


def invalid_token():
    """令牌无效响应（401），返回WWW-Authenticate头"""
    server_error(status.HTTP_401_UNAUTHORIZED, "Invalid token", {"WWW-Authenticate": "Bearer"})


def invalid_permission(detail="没有权限"):
    """权限不足响应（403）"""
    server_error(status.HTTP_403_FORBIDDEN, detail)


class JsonExtendResponse(JSONResponse):
    """使用扩展编码器的JSON响应，支持日期、小数等类型"""

    def render(self, content):
        return json.dumps(content, cls=tools.JsonExtendEncoder).encode("utf-8")


def vrm_json_response(code: int, message: str, data: any):
    """
    构建统一的JSON响应

    Args:
        code: 状态码
            200 - 请求成功
            400 - 客户端请求语法错误
            401 - 需要身份认证
            500 - 服务器内部错误
        message: 消息
        data: 数据

    Returns:
        JSON响应
    """
    return JsonExtendResponse(
        {
            "code": code,
            "message": message,
            "data": data,
            "time": tools.datetime_to_string(),
        }
    )


def vrm_ok_json_response(data=None, message="success", code=200):
    """成功响应（200）"""
    return vrm_json_response(code=code, message=message, data=data)


def vrm_error_json_response(code: int, message="error", data=None):
    """错误响应"""
    return vrm_json_response(code=code, message=message, data=data)


def jsonify(data=None, message="成功"):
    """简易的JSON响应（兼容旧接口）"""
    return JsonExtendResponse(
        {
            "code": 200,
            "message": message,
            "data": data,
            "success": True,
            "time": tools.datetime_to_string(),
        }
    )


def get_pagination_structure(totals: int, data: list[dict]):
    """构建分页响应结构"""
    return {"totals": totals, "data": data}


def sse_struct(data: dict):
    """构建SSE（Server-Sent Events）格式的数据"""
    return f"data: {tools.dict_to_json_ea(data)}\n\n"
