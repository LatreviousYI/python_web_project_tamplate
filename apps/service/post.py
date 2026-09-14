"""
内容业务层

负责文章 / 问答（统一 Post）的查询与增删改。
DB 会话由路由通过 common.db.get_session 注入，当前阶段不连库、不执行。
"""

import datetime
from typing import Optional

from vorm import Session, col

from apps.model.post import Post
from utils.response_utils import abort

# 用户可切换的状态：草稿 ↔ 待审核；published 只能由系统审核通过后置入
USER_EDITABLE_STATUS = frozenset({"draft", "pending"})


async def list_posts(
    session: Session,
    page: int = 1,
    page_size: int = 20,
    post_type: Optional[str] = None,
) -> dict:
    query = session.query(Post)
    if post_type:
        query = query.filter(Post.type == post_type)
    totals = await query.count()
    posts = await query.order_by(col(Post.created_at).desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"totals": totals, "data": posts}


async def create_post(
    session: Session,
    user_id: int,
    title: str,
    content: str,
    post_type: str = "article",
    summary: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Post:
    post = Post(
        user_id=user_id,
        type=post_type,
        title=title,
        content=content,
        summary=summary,
        tags=tags or [],
    )
    await session.save(post)
    return post


async def get_post(session: Session, post_id: int) -> Post | None:
    # 浏览量原子自增（model 层统一封装）
    affected = await Post.incr_count(session, post_id, "view_count")
    if not affected:
        return None
    return await session.query(Post).filter(Post.id == post_id).first()


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
