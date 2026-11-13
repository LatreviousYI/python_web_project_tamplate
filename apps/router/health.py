from fastapi import APIRouter

from utils.response_utils import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> ApiResponse:
    """进程健康检查，不依赖数据库和外部服务。"""
    return ApiResponse(data={"status": "ok"})
