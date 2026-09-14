"""
内容路由

文章 / 问答 统一走 /posts，type 参数区分（article / qa）。
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, StringConstraints

from apps import dependencies
from apps.model.post import Post
from apps.service import post as post_service
from common.db import get_session
from utils.response_utils import ApiResponse, PageResult

router = APIRouter(prefix="/posts")


class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    summary: str | None = None
    tags: list[str] | None = None


class PostStatusUpdate(BaseModel):
    status: Literal["draft", "pending"]


class PostCreate(PostStatusUpdate):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    type: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    summary: str | None = None
    tags: list[str] = []
    status: Literal["draft", "pending"] = "draft"


@router.get("")
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None),
    session=Depends(get_session),
    user_id: int | None = Depends(dependencies.get_optional_user),
) -> ApiResponse:
    result = await post_service.list_posts(session, page, page_size, type, user_id)
    return ApiResponse(data=PageResult(totals=result["totals"], data=result["data"]))


@router.get("/mine")
async def list_my_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None),
    status: Literal["draft", "pending", "published"] | None = Query(None),
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    """个人中心：我的内容列表（含草稿 / 待审核 / 已发布），可按类型 / 状态筛选。"""
    result = await post_service.list_my_posts(session, user_id, page, page_size, type, status)
    return ApiResponse(data=PageResult(totals=result["totals"], data=result["data"]))


@router.post("")
async def create_post(
    payload: PostCreate,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    post = Post(
        user_id=user_id,
        type=payload.type,
        title=payload.title,
        content=payload.content,
        summary=payload.summary,
        tags=payload.tags or [],
        status=payload.status,
    )
    await session.save(post)
    return ApiResponse(data=post)


@router.get("/{post_id}")
async def get_post(
    post_id: int,
    session=Depends(get_session),
    user_id: int | None = Depends(dependencies.get_optional_user),
) -> ApiResponse:
    post = await post_service.get_post(session, post_id, user_id)
    if post is None:
        return ApiResponse(code=404, message="post not found")
    return ApiResponse(data=post)


@router.put("/{post_id}")
async def update_post(
    post_id: int,
    payload: PostUpdate,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    post = await post_service.update_post(session, post_id, user_id, **payload.model_dump(exclude_unset=True))
    if post is None:
        return ApiResponse(code=404, message="post not found")
    return ApiResponse(data=post)


@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    post = await post_service.delete_post(session, post_id, user_id)
    if post is None:
        return ApiResponse(code=404, message="post not found")
    return ApiResponse()


@router.patch("/{post_id}/status")
async def set_post_status(
    post_id: int,
    payload: PostStatusUpdate,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    post = await post_service.set_post_status(session, post_id, user_id, payload.status)
    if post is None:
        return ApiResponse(code=404, message="post not found")
    return ApiResponse(data=post)


@router.post("/{post_id}/publish")
async def submit_post(
    post_id: int,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    """个人中心发布草稿：draft → pending（提交审核；published 由系统审核后置入）。"""
    post = await post_service.set_post_status(session, post_id, user_id, "pending")
    if post is None:
        return ApiResponse(code=404, message="post not found")
    return ApiResponse(data=post)


@router.post("/{post_id}/like")
async def like_post(
    post_id: int,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    post = await post_service.like_post(session, post_id, user_id)
    if post is None:
        return ApiResponse(code=404, message="post not found")
    return ApiResponse(data=post)
