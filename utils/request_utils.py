"""
请求解析工具模块

提供请求体的解析功能，用于FastAPI接口中获取JSON请求体
"""

from fastapi import Request
from starlette.requests import ClientDisconnect

from utils import log_util, response_utils


class GetPostJsonBody:
    """
    获取POST请求的JSON Body

    用于FastAPI接口中作为Depends依赖，解析请求体为字典
    """

    async def __call__(self, request: Request):
        """
        解析请求体为JSON字典

        Args:
            request: FastAPI请求对象

        Returns:
            请求体字典

        Raises:
            HTTPException: 解析失败时抛出400错误
        """
        try:
            return await request.json()
        except ClientDisconnect as e:
            log_util.logger.exception(f"客户端意外断开链接: {e}")
            raise response_utils.invalid_params()
        except Exception as e:
            log_util.logger.exception(e)
            raise response_utils.invalid_params()
