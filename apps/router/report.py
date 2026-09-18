"""
技术月报路由（统计接口，需鉴权）

- GET /reports/summary            当月统计（技术文章 / 问答 / 项目数量）
- GET /reports/hot-articles       热门文章 top3（当月点赞）
- GET /reports/hot-discussions    热门讨论 top3（当月回复）
- GET /reports/hot-projects       热门项目 top3（当月点赞）
- GET /reports/trending-topics    趋势话题（当月文章标签）
"""

from fastapi import APIRouter, Depends

from apps import dependencies
from apps.service import report as report_service
from common.db import get_session
from utils.response_utils import ApiResponse

router = APIRouter(prefix="/reports")


@router.get("/summary")
async def get_summary(
    session=Depends(get_session),
    _user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    return ApiResponse(data=await report_service.summary(session))


@router.get("/hot-articles")
async def get_hot_articles(
    session=Depends(get_session),
    _user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    return ApiResponse(data=await report_service.hot_articles(session))


@router.get("/hot-discussions")
async def get_hot_discussions(
    session=Depends(get_session),
    _user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    return ApiResponse(data=await report_service.hot_discussions(session))


@router.get("/hot-projects")
async def get_hot_projects(
    session=Depends(get_session),
    _user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    return ApiResponse(data=await report_service.hot_projects(session))


@router.get("/trending-topics")
async def get_trending_topics(
    session=Depends(get_session),
    _user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    return ApiResponse(data=await report_service.trending_topics(session))
