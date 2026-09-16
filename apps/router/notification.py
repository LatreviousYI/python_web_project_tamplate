"""
通知路由

- GET    /notifications                   通知列表（分页，unread 可选过滤）
- GET    /notifications/unread-count      未读数量
- POST   /notifications/{id}/read         单条已读
- POST   /notifications/read-all          全部已读
- DELETE /notifications/{id}              删除单条通知
- DELETE /notifications/read-all          删除全部已读通知
"""

from fastapi import APIRouter, Depends, Query

from apps import dependencies
from apps.service import notification as notification_service
from common.db import get_session
from utils.response_utils import ApiResponse, PageResult

router = APIRouter(prefix="/notifications")


@router.get("")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread: bool | None = Query(None),
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    result = await notification_service.list_notifications(session, user_id, page, page_size, unread)
    return ApiResponse(data=PageResult(totals=result["totals"], data=result["data"]))


@router.get("/unread-count")
async def get_unread_count(
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    count = await notification_service.unread_count(session, user_id)
    return ApiResponse(data={"count": count})


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    ok = await notification_service.mark_read(session, user_id, notification_id)
    if not ok:
        return ApiResponse(code=404, message="notification not found")
    return ApiResponse()


@router.post("/read-all")
async def mark_all_read(
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    await notification_service.mark_all_read(session, user_id)
    return ApiResponse()


@router.delete("/read-all")
async def delete_all_read(
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    await notification_service.delete_all_read(session, user_id)
    return ApiResponse()


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    ok = await notification_service.delete_notification(session, user_id, notification_id)
    if not ok:
        return ApiResponse(code=404, message="notification not found")
    return ApiResponse()
