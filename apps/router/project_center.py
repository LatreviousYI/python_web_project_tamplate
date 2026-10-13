"""
项目中心路由

- GET    /projects              项目列表（本地库）
- POST   /projects              新建项目（本地落库，不再跳转云效）
- GET    /projects/contributors 贡献者候选用户（服务端模糊搜索 + 限量）
- GET    /projects/{project_id} 项目详情（本地库）
- PUT    /projects/{project_id} 编辑项目（仅创建者）
- DELETE /projects/{project_id} 删除项目（仅创建者，软删除，不动项目下内容）
- POST   /projects/{project_id}/like 点赞 / 取消赞
"""

from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, StringConstraints, field_validator

from apps import dependencies
from apps.service import project_center as project_center_service
from common.db import get_session
from utils.response_utils import ApiResponse, PageResult

router = APIRouter(prefix="/projects")

# 与 osc_project.repo_url（VARCHAR(500)）保持一致，超出会在 ORM 层抛校验异常变成 500
_REPO_URL_MAX_LENGTH = 500


def _is_scp_like_ssh_url(url: str) -> bool:
    """SCP 形式的 SSH 地址：user@host:path（host 必须含「.」，path 非空）。"""
    at = url.find("@")
    if at <= 0:
        return False
    colon = url.find(":", at)
    if colon < 0:
        return False
    host = url[at + 1 : colon]
    path = url[colon + 1 :]
    return "." in host and len(path) > 0


def _validate_repo_url(value: str | None) -> str | None:
    """仓库链接选填：留空合法（原样返回 ""，表示清空链接）；填写了必须是合法仓库地址。

    与前端 `src/utils/format.ts#isValidRepoUrl` 保持同一套规则，支持：
    - http(s)://host/path
    - ssh://[user@]host[:port]/path
    - SCP 形式 user@host:path（如 git@github.com:org/repo.git）
    """
    if value is None:
        return None
    url = value.strip()
    if not url:
        return ""
    if len(url) > _REPO_URL_MAX_LENGTH:
        raise ValueError(f"仓库链接长度不能超过 {_REPO_URL_MAX_LENGTH} 个字符")
    if any(ch.isspace() for ch in url):
        raise ValueError("仓库链接不能包含空格")

    if _is_scp_like_ssh_url(url):
        return url

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", "ssh"):
        raise ValueError("仓库链接必须以 http://、https:// 或 ssh:// 开头")
    if "." not in parsed.netloc:
        raise ValueError("仓库链接的域名不合法")
    return url


class ProjectCreate(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    summary: str | None = None
    tags: Annotated[list[str], Field(min_length=1)]
    repo_url: str | None = None
    contributor_ids: list[int] | None = None

    @field_validator("repo_url")
    @classmethod
    def check_repo_url(cls, value: str | None) -> str | None:
        return _validate_repo_url(value)


class ProjectUpdate(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    summary: str | None = None
    tags: Annotated[list[str], Field(min_length=1)] | None = None
    repo_url: str | None = None
    contributor_ids: list[int] | None = None

    @field_validator("repo_url")
    @classmethod
    def check_repo_url(cls, value: str | None) -> str | None:
        return _validate_repo_url(value)


@router.get("")
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    mine: bool = Query(False, description="仅返回当前用户创建的项目"),
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    result = await project_center_service.list_projects(session, page, page_size, user_id, mine)
    return ApiResponse(data=PageResult(totals=result["totals"], data=result["data"]))


@router.post("")
async def create_project(
    payload: ProjectCreate,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    """新建项目：本地落库（标题 / 简介 / 标签 / 仓库链接 / 贡献者），响应结构与详情一致。"""
    project = await project_center_service.create_project(
        session,
        user_id,
        payload.title,
        payload.summary,
        payload.tags,
        payload.repo_url,
        payload.contributor_ids,
    )
    return ApiResponse(data=project)


@router.get("/contributors")
async def list_contributor_users(
    keyword: str | None = Query(None, max_length=100, description="按用户名 / 姓名模糊搜索"),
    limit: int = Query(20, ge=1, le=100, description="返回条数上限"),
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    """贡献者候选用户：排除当前用户，服务端模糊搜索 + 限量（默认 20，最多 100）。"""
    users = await project_center_service.list_registered_users(session, keyword, limit, exclude_user_id=user_id)
    return ApiResponse(data=users)


@router.get("/{project_id}")
async def get_project_detail(
    project_id: int,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    """项目详情（项目关联的文章/问答请用 /posts?project_id= 列表接口单独查询）。"""
    detail = await project_center_service.get_project_detail(session, project_id, user_id)
    if detail is None:
        return ApiResponse(code=404, message="project not found")
    return ApiResponse(data=detail)


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    """编辑项目，仅创建者可改（可选字段，空字符串或 null 可清空 summary / repo_url）。

    响应结构与详情一致（不是裸项目行）。
    """
    project = await project_center_service.update_project(
        session, project_id, user_id, **payload.model_dump(exclude_unset=True)
    )
    if project is None:
        return ApiResponse(code=404, message="project not found")
    return ApiResponse(data=project)


@router.post("/{project_id}/like")
async def like_project(
    project_id: int,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    """点赞 / 取消赞（切换式）；项目不存在或已删除返回 404。"""
    result = await project_center_service.like_project(session, project_id, user_id)
    if result is None:
        return ApiResponse(code=404, message="project not found")
    return ApiResponse(data=result)


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    session=Depends(get_session),
    user_id: int = Depends(dependencies.get_current_user),
) -> ApiResponse:
    """删除项目（仅创建者）：软删除，只标记 osc_project.is_deleted。

    项目下的文章 / 问答及其回复、点赞、贡献者记录全部保留，不随项目一起删除。
    """
    result = await project_center_service.delete_project(session, project_id, user_id)
    if result == "not_found":
        return ApiResponse(code=404, message="project not found")
    return ApiResponse()
