from fastapi import APIRouter, Depends, Query

from apps import dependencies
from apps.service import tag as tag_service
from common.db import get_session
from utils.response_utils import ApiResponse

router = APIRouter(prefix="/tags")


@router.get("")
async def get_tag_suggestions(
    keyword: str | None = Query(None, max_length=100),
    limit: int = Query(20, ge=1, le=100),
    session=Depends(get_session),
    _user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    return ApiResponse(data=await tag_service.tag_suggestions(session, keyword, limit))
