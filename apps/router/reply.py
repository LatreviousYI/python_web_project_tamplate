"""
回复路由

- GET    /posts/{post_id}/replies    一级回复列表（附每条的二级回复数）
- GET    /replies/{reply_id}/replies 某条一级回复下的二级回复（分页）
- POST   /posts/{post_id}/replies    发表回复
- DELETE /replies/{reply_id}         删除回复
- POST   /replies/{reply_id}/vote    点赞/点踩（切换式）
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from apps import dependencies
from apps.service import reply as reply_service
from common.db import get_session
from utils.response_utils import ApiResponse, PageResult

router = APIRouter()


class ReplyCreate(BaseModel):
    content: str
    reply_to: int | None = None
    reply_to_user_id: int | None = None


class ReplyVoteCreate(BaseModel):
    vote_type: Literal["like", "dislike"]


@router.get("/posts/{post_id}/replies")
async def list_first_level_replies(
    post_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session=Depends(get_session),
) -> ApiResponse:
    result = await reply_service.list_first_level_replies(session, post_id, page, page_size)
    if result is None:
        return ApiResponse(code=404, message="post not found")
    return ApiResponse(data=PageResult(totals=result["totals"], data=result["data"]))


@router.get("/replies/{reply_id}/replies")
async def list_sub_replies(
    reply_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session=Depends(get_session),
) -> ApiResponse:
    result = await reply_service.list_sub_replies(session, reply_id, page, page_size)
    if result is None:
        return ApiResponse(code=404, message="reply not found")
    return ApiResponse(data=PageResult(totals=result["totals"], data=result["data"]))


@router.post("/posts/{post_id}/replies")
async def create_reply(
    post_id: int,
    payload: ReplyCreate,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    reply = await reply_service.create_reply(
        session,
        post_id,
        user_id,
        payload.content,
        payload.reply_to,
        payload.reply_to_user_id,
    )
    if reply is None:
        return ApiResponse(code=404, message="post not found")
    return ApiResponse(data=reply)


@router.delete("/replies/{reply_id}")
async def delete_reply(
    reply_id: int,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    reply = await reply_service.delete_reply(session, reply_id, user_id)
    if reply is None:
        return ApiResponse(code=404, message="reply not found")
    return ApiResponse()


@router.post("/replies/{reply_id}/vote")
async def vote_reply(
    reply_id: int,
    payload: ReplyVoteCreate,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    reply = await reply_service.vote_reply(session, reply_id, user_id, payload.vote_type)
    if reply is None:
        return ApiResponse(code=404, message="reply not found")
    return ApiResponse(data=reply)
