"""
项目中心路由

- GET /projects  代码仓库（项目）列表：直接透传云效仓库数据 + 匹配创作者姓名
"""

from fastapi import APIRouter, Depends, Query

from apps import dependencies
from apps.service import project_center as project_center_service
from common.db import get_session
from utils.response_utils import ApiResponse, PageResult

router = APIRouter(prefix="/projects")


@router.get("")
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    result = await project_center_service.list_repositories(session, page, page_size)
    return ApiResponse(data=PageResult(totals=result["totals"], data=result["data"]))


@router.get("/{project_id}")
async def get_project_detail(
    project_id: int,
    session=Depends(get_session),
    _=Depends(dependencies.get_current_user),
) -> ApiResponse:
    """仓库详情（项目关联的文章/问答请用 /posts?project_id= 列表接口单独查询）。"""
    detail = await project_center_service.get_repository_detail(session, project_id)
    return ApiResponse(data=detail)
