"""
内容业务层

负责文章 / 问答（统一 Post）的查询与增删改。
DB 会话由路由通过 common.db.get_session 注入，当前阶段不连库、不执行。
"""

import datetime
from typing import Optional

from vorm import Session, col

from apps.model.auth import User
from apps.model.post import Post, PostLike
from utils.response_utils import abort

# 用户可切换的状态：草稿 ↔ 待审核；published 只能由系统审核通过后置入
USER_EDITABLE_STATUS = frozenset({"draft", "pending"})


async def _liked_post_ids(session: Session, user_id: Optional[int], post_ids: list[int]) -> set[int]:
    """批量查询当前用户已点赞的内容 id 集合（避免列表 N+1）。"""
    if user_id is None or not post_ids:
        return set()
    likes = await session.query(PostLike).filter(col(PostLike.user_id) == user_id, col(PostLike.post_id).in_(post_ids)).all()
    return {l.post_id for l in likes}


def _user_summary(user: User) -> dict:
    """内容作者的最小用户信息（不泄露手机号 / 邮箱 / 租户）。"""
    return {"id": user.id, "user_name": user.user_name, "name": user.name, "avatar": user.avatar}


async def _user_summary_map(session: Session, user_ids: set[int]) -> dict[int, dict]:
    """批量查询作者最小信息（避免列表 N+1）。"""
    if not user_ids:
        return {}
    users = await session.query(User).filter(col(User.id).in_(user_ids)).all()
    return {u.id: _user_summary(u) for u in users}


async def list_posts(
    session: Session,
    page: int = 1,
    page_size: int = 20,
    post_type: Optional[str] = None,
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> dict:
    query = session.query(Post).filter(Post.status == "published")  # 仅已发布对外展示（草稿/待审核走个人中心）
    if post_type:
        query = query.filter(Post.type == post_type)
    if project_id is not None:
        query = query.filter(Post.project_id == project_id)
    totals = await query.count()
    posts = await query.order_by(col(Post.created_at).desc()).offset((page - 1) * page_size).limit(page_size).all()
    liked_ids = await _liked_post_ids(session, user_id, [p.id for p in posts])
    user_map = await _user_summary_map(session, {p.user_id for p in posts})
    data = [{**p.model_dump(mode="json"), "liked": p.id in liked_ids, "user": user_map.get(p.user_id)} for p in posts]
    return {"totals": totals, "data": data}


async def list_my_posts(
    session: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    post_type: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """个人中心：当前用户自己的全部内容（含草稿 / 待审核 / 已发布），可按类型 / 状态筛选。"""
    query = session.query(Post).filter(Post.user_id == user_id)
    if post_type:
        query = query.filter(Post.type == post_type)
    if status:
        query = query.filter(Post.status == status)
    totals = await query.count()
    posts = await query.order_by(col(Post.created_at).desc()).offset((page - 1) * page_size).limit(page_size).all()
    liked_ids = await _liked_post_ids(session, user_id, [p.id for p in posts])
    user_map = await _user_summary_map(session, {p.user_id for p in posts})
    data = [{**p.model_dump(mode="json"), "liked": p.id in liked_ids, "user": user_map.get(p.user_id)} for p in posts]
    return {"totals": totals, "data": data}


async def create_post(
    session: Session,
    user_id: int,
    title: str,
    content: str,
    post_type: str = "article",
    summary: Optional[str] = None,
    tags: Optional[list[str]] = None,
    project_id: Optional[int] = None,
) -> Post:
    post = Post(
        user_id=user_id,
        type=post_type,
        title=title,
        content=content,
        summary=summary,
        tags=tags or [],
        project_id=project_id,
    )
    await session.save(post)
    return post


async def get_post(session: Session, post_id: int, user_id: Optional[int] = None) -> dict | None:
    post = await session.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return None
    # 未发布内容（草稿/待审核）仅作者本人可见（个人中心上线前，非作者一律视为不存在）
    if post.status != "published" and post.user_id != user_id:
        return None
    # 浏览量原子自增（model 层统一封装）
    await Post.incr_count(session, post_id, "view_count")
    post = await session.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return None
    liked = post_id in await _liked_post_ids(session, user_id, [post_id])
    author = await session.query(User).filter(User.id == post.user_id).first()
    return {
        **post.model_dump(mode="json"),
        "liked": liked,
        "user": _user_summary(author) if author else None,
    }


async def update_post(session: Session, post_id: int, user_id: int, **fields) -> Post | None:
    post = await session.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
    if post is None:
        return None
    # None 表示「不更新该字段」
    for key, value in fields.items():
        if value is not None:
            setattr(post, key, value)
    await session.save(post)
    return post


async def delete_post(session: Session, post_id: int, user_id: int) -> Post | None:
    post = await session.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
    if post is None:
        return None
    # TODO: 关联回复的清理（软删 / 级联）待补
    await session.delete(post)
    return post


async def set_post_status(session: Session, post_id: int, user_id: int, status: str) -> Post | None:
    """用户提交发布 / 撤回：draft ↔ pending（published 由系统控制，用户不可直接修改）。"""
    if status not in USER_EDITABLE_STATUS:
        abort(400, f"非法状态: {status}")
    post = await session.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
    if post is None:
        return None
    if post.status == "published":
        abort(400, "已发布内容的状态由系统控制，用户不能修改")
    post.status = status
    await session.save(post)
    return post


async def publish_post(session: Session, post_id: int) -> Post | None:
    """系统审核通过后真正发布：pending → published。"""
    post = await session.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return None
    post.status = "published"
    post.published_at = datetime.datetime.now()
    await session.save(post)
    return post


async def reject_post(session: Session, post_id: int) -> Post | None:
    """系统审核不通过，打回草稿：pending → draft。"""
    post = await session.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return None
    post.status = "draft"
    await session.save(post)
    return post


async def like_post(session: Session, post_id: int, user_id: int) -> Post | None:
    """点赞 / 取消赞（切换式）：
    - 未赞 → 插入记录 + like_count +1
    - 已赞 → 取消：删记录 + like_count -1

    返回最新内容（含最新计数）；post_id 不存在时返回 None。
    """
    post = await session.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return None

    existing = await session.query(PostLike).filter(PostLike.post_id == post_id, PostLike.user_id == user_id).first()

    if existing is None:
        # 首次点赞：插入记录 + 计数 +1
        await session.save(PostLike(post_id=post_id, user_id=user_id))
        await Post.incr_count(session, post_id, "like_count", 1)
    else:
        # 重复点赞 → 取消：删记录 + 计数 -1
        await session.delete(existing)
        await Post.incr_count(session, post_id, "like_count", -1)

    return await session.query(Post).filter(Post.id == post_id).first()
