"""
项目中心业务层

项目本地落库（osc_project）：列表 / 详情 / 新建 / 编辑 / 点赞 / 软删除。

本模块已与云效解耦：不再同步云效组织成员、不再透传云效仓库，
仓库链接仅作为普通字符串保存（格式在路由层校验），项目元信息以本地库为唯一来源。
"""

from typing import Optional

from vorm import Session, col

from apps.model.auth import User
from apps.model.project_center import Project, ProjectContributor, ProjectLike

# 允许通过「传 null 或空字符串」清空的字段白名单。
# 其余字段拒绝 null，避免把 NOT NULL 列写成 NULL（例如 title）。
_CLEARABLE_FIELDS = frozenset({"summary", "repo_url"})

# 贡献者候选列表的默认 / 最大返回条数
_CONTRIBUTOR_DEFAULT_LIMIT = 20
_CONTRIBUTOR_MAX_LIMIT = 100

# 用于区分「未传该字段」与「显式传了 null」
_UNSET: object = object()


def _user_summary(user: User) -> dict:
    """贡献者最小用户信息（不泄露手机号 / 邮箱 / 租户）。"""
    return {"id": user.id, "user_name": user.user_name, "name": user.name, "avatar": user.avatar}


async def _creator_info_map(session: Session, user_ids: set[int]) -> dict[int, tuple[str | None, str | None]]:
    """批量查询创建者展示信息，避免列表 N+1。"""
    if not user_ids:
        return {}
    users = await session.query(User).filter(col(User.id).in_(user_ids)).all()
    return {u.id: (u.name or u.user_name, u.avatar) for u in users}


async def _project_like_stats(session: Session, project_ids: list[int], user_id: int | None) -> tuple[dict[int, int], set[int]]:
    """一次查询批量统计每个项目的点赞数与当前用户是否已赞。"""
    if not project_ids:
        return {}, set()
    likes = await session.query(ProjectLike).filter(col(ProjectLike.project_id).in_(project_ids)).all()
    count_map: dict[int, int] = {}
    liked_set: set[int] = set()
    for like in likes:
        count_map[like.project_id] = count_map.get(like.project_id, 0) + 1
        if user_id is not None and like.user_id == user_id:
            liked_set.add(like.project_id)
    return count_map, liked_set


async def _contributor_map(session: Session, project_ids: list[int]) -> dict[int, list[dict]]:
    """批量查询每个项目的贡献者（用户最小信息），避免列表 N+1。返回 {project_id: [user_summary, ...]}。"""
    if not project_ids:
        return {}
    rows = await session.query(ProjectContributor).filter(col(ProjectContributor.project_id).in_(project_ids)).all()
    user_ids = {row.user_id for row in rows}
    if not user_ids:
        return {}
    users = await session.query(User).filter(col(User.id).in_(user_ids)).all()
    user_map = {u.id: _user_summary(u) for u in users}
    result: dict[int, list[dict]] = {}
    for row in rows:
        summary = user_map.get(row.user_id)
        if summary is not None:
            result.setdefault(row.project_id, []).append(summary)
    return result


async def _existing_user_ids(session: Session, user_ids: set[int]) -> set[int]:
    """过滤出真实存在于 osc_user 的主键 id，用于贡献者写入校验。"""
    if not user_ids:
        return set()
    users = await session.query(User).filter(col(User.id).in_(user_ids)).all()
    return {u.id for u in users}


def _project_payload(
    project: Project,
    user_id: int | None,
    creator_map: dict[int, tuple[str | None, str | None]],
    count_map: dict[int, int],
    liked_set: set[int],
    contributor_map: dict[int, list[dict]] | None = None,
) -> dict:
    """项目序列化：本地字段 + creator info / contributors / like_count / liked / can_edit。

    `is_deleted` 是内部软删除标记（对外只返回未删除项目），因此不写进响应体。
    """
    data = project.model_dump(mode="json")
    data.pop("is_deleted", None)
    creator_name, creator_avatar = creator_map.get(project.user_id, (None, None))
    data.update(
        {
            "creator_name": creator_name,
            "creator_avatar": creator_avatar,
            "contributors": (contributor_map or {}).get(project.id, []),
            "like_count": count_map.get(project.id, 0),
            "liked": project.id in liked_set,
            "can_edit": project.user_id == user_id,
        }
    )
    return data


async def _single_project_payload(session: Session, project: Project, user_id: int | None) -> dict:
    """单个项目的完整对外结构（详情 / 新建 / 编辑统一使用，保证响应结构一致）。"""
    creator_map = await _creator_info_map(session, {project.user_id})
    count_map, liked_set = await _project_like_stats(session, [project.id], user_id)
    contributor_map = await _contributor_map(session, [project.id])
    return _project_payload(project, user_id, creator_map, count_map, liked_set, contributor_map)


async def list_projects(
    session: Session,
    page: int = 1,
    page_size: int = 10,
    user_id: int | None = None,
    mine: bool = False,
) -> dict:
    """项目列表（本地库，不含已软删除），按创建时间倒序分页。

    mine=True 时仅返回当前用户创建的项目。返回 {"totals": 总数量, "data": [...]}。
    """
    query = session.query(Project).filter(Project.is_deleted == False)  # noqa: E712
    if mine and user_id is not None:
        query = query.filter(Project.user_id == user_id)
    total = await query.count()
    projects = await (
        query.order_by(col(Project.created_at).desc(), col(Project.id).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    creator_map = await _creator_info_map(session, {p.user_id for p in projects})
    count_map, liked_set = await _project_like_stats(session, [p.id for p in projects], user_id)
    contributor_map = await _contributor_map(session, [p.id for p in projects])
    data = [_project_payload(p, user_id, creator_map, count_map, liked_set, contributor_map) for p in projects]
    return {"totals": total, "data": data}


async def list_registered_users(
    session: Session,
    keyword: str | None = None,
    limit: int = _CONTRIBUTOR_DEFAULT_LIMIT,
    exclude_user_id: int | None = None,
) -> list[dict]:
    """贡献者候选用户（已注册用户最小信息），服务端模糊搜索 + 限量。

    - keyword 同时模糊匹配 user_name 与 name，不传则返回最早注册的用户；
    - limit 限制在 1 ~ 100，避免一次拉全表。
    - exclude_user_id 在限量前排除当前用户。
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = _CONTRIBUTOR_DEFAULT_LIMIT
    limit = max(1, min(limit, _CONTRIBUTOR_MAX_LIMIT))

    query = session.query(User)
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        query = query.filter(col(User.user_name).like(pattern) | col(User.name).like(pattern))
    users = await query.order_by(col(User.id).asc()).limit(limit).all()
    return [_user_summary(u) for u in users]


async def count_projects(session: Session) -> int:
    """项目总数（本地库，不含已软删除）。"""
    return await session.query(Project).filter(Project.is_deleted == False).count()  # noqa: E712


async def get_project_detail(session: Session, project_id: int, user_id: int | None = None) -> dict | None:
    """单个项目详情（本地库）；不存在或已软删除返回 None。"""
    project = (
        await session.query(Project)
        .filter(Project.id == project_id, Project.is_deleted == False)  # noqa: E712
        .first()
    )
    if project is None:
        return None
    return await _single_project_payload(session, project, user_id)


async def _replace_contributors(session: Session, project_id: int, contributor_ids: list[int] | None, creator_id: int) -> None:
    """全量替换项目贡献者（按用户主键去重），列表为空则清空。

    只写入真实存在于 osc_user 的其他用户 id（静默丢弃创建者及无效 id），
    避免客户端提交任意整数产生孤儿贡献者记录。
    """
    target_ids = {int(uid) for uid in (contributor_ids or [])}
    target_ids.discard(creator_id)
    target_ids &= await _existing_user_ids(session, target_ids)

    existing = await session.query(ProjectContributor).filter(ProjectContributor.project_id == project_id).all()
    existing_ids = {row.user_id for row in existing}
    for row in existing:
        if row.user_id not in target_ids:
            await session.delete(row)
    for uid in target_ids - existing_ids:
        await session.save(ProjectContributor(project_id=project_id, user_id=uid))


async def create_project(
    session: Session,
    user_id: int,
    title: str,
    summary: str | None = None,
    tags: list | None = None,
    repo_url: str | None = None,
    contributor_ids: list[int] | None = None,
) -> dict:
    """新建项目（本地落库）。仓库链接选填：格式已在路由层校验，这里把空值统一存为 None。

    返回与详情完全一致的项目结构。
    """
    project = Project(
        user_id=user_id,
        title=title,
        summary=summary,
        tags=tags or [],
        repo_url=repo_url or None,
    )
    await session.save(project)
    await _replace_contributors(session, project.id, contributor_ids, user_id)
    return await _single_project_payload(session, project, user_id)


async def update_project(session: Session, project_id: int, user_id: int, **fields) -> dict | None:
    """编辑项目（仅创建者），返回更新后的完整项目结构；不存在 / 非创建者 / 已删除返回 None。

    约定：
    - 未出现在入参中的字段保持原值；
    - `summary` / `repo_url` 传 `null` 或空字符串表示清空（置 NULL）；
    - 其余字段不接受 `null`（忽略），避免把 NOT NULL 列写成 NULL；
    - 字段值没有实际变化时不写库，因此不会无谓刷新 `updated_at`；
    - `contributor_ids` 传列表则整体替换（传空列表清空所有贡献者），未传则不更新。
    """
    contributor_ids = fields.pop("contributor_ids", _UNSET)

    project = (
        await session.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == user_id,
            Project.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if project is None:
        return None

    changed = False
    for key, value in fields.items():
        if key in _CLEARABLE_FIELDS and isinstance(value, str) and not value.strip():
            # 仓库链接 / 简介选填：传空字符串表示清空
            value = None
        if value is None and key not in _CLEARABLE_FIELDS:
            continue
        if getattr(project, key) != value:
            setattr(project, key, value)
            changed = True
    if changed:
        await session.save(project)

    if contributor_ids is not _UNSET:
        await _replace_contributors(session, project.id, contributor_ids, user_id)

    return await _single_project_payload(session, project, user_id)


async def like_project(session: Session, project_id: int, user_id: int) -> dict | None:
    """项目点赞 / 取消赞（切换式），返回 {"liked": bool, "like_count": int}。

    项目不存在或已软删除时返回 None（路由转 404），避免写入指向不存在项目的孤儿点赞记录。
    """
    project = (
        await session.query(Project)
        .filter(Project.id == project_id, Project.is_deleted == False)  # noqa: E712
        .first()
    )
    if project is None:
        return None

    existing = await session.query(ProjectLike).filter(ProjectLike.project_id == project_id, ProjectLike.user_id == user_id).first()
    if existing is None:
        await session.save(ProjectLike(project_id=project_id, user_id=user_id))
    else:
        await session.delete(existing)
    liked = existing is None
    like_count = await session.query(ProjectLike).filter(ProjectLike.project_id == project_id).count()
    return {"liked": liked, "like_count": like_count}


async def delete_project(session: Session, project_id: int) -> str:
    """软删除项目（仅创建者），返回结果状态：

    - "not_found"：项目不存在、已删除，或当前用户不是创建者（不泄露他人项目是否存在）
    - "ok"：软删除成功

    只把 `osc_project.is_deleted` 置 1，**不删除任何关联数据**：
    项目下的文章 / 问答、回复、点赞、贡献者记录全部原样保留，可按需恢复。
    """
    project = (
        await session.query(Project)
        .filter(
            Project.id == project_id,
            Project.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if project is None:
        return "not_found"

    project.is_deleted = True
    await session.save(project)
    return "ok"
