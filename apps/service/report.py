"""
技术月报业务层

提供当月统计、热门文章 / 讨论 / 项目、趋势话题等聚合查询。

口径约定：
- 「当月」= created_at ∈ [本月 1 日 00:00:00, 下月 1 日 00:00:00)（naive 本地时间）
- 仅统计已发布（published）内容，草稿 / 待审核不进入公开月报
- 热门榜取前 3（_TOP_N）
"""

import datetime

from vorm import Session, col

from apps.model.auth import User
from apps.model.post import Post
from apps.model.project_center import Project, ProjectLike
from apps.service import project_center as project_center_service
from apps.service.tag import count_tags

# 热门榜前 N 条
_TOP_N = 3


def _current_month_range() -> tuple[datetime.datetime, datetime.datetime]:
    """返回本月起止时间：(本月 1 日 00:00:00, 下月 1 日 00:00:00)。"""
    now = datetime.datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        end = datetime.datetime(now.year + 1, 1, 1)
    else:
        end = datetime.datetime(now.year, now.month + 1, 1)
    return start, end


def _user_summary(user: User) -> dict:
    """作者最小用户信息（不泄露手机号 / 邮箱 / 租户）。"""
    return {"id": user.id, "user_name": user.user_name, "name": user.name, "avatar": user.avatar}


async def _user_summary_map(session: Session, user_ids: set[int]) -> dict[int, dict]:
    """批量查询作者最小信息（避免列表 N+1）。"""
    if not user_ids:
        return {}
    users = await session.query(User).filter(col(User.id).in_(user_ids)).all()
    return {u.id: _user_summary(u) for u in users}


async def _attach_authors(session: Session, posts: list[Post]) -> list[dict]:
    """给内容列表附加作者摘要。"""
    if not posts:
        return []
    user_map = await _user_summary_map(session, {p.user_id for p in posts})
    return [{**p.model_dump(mode="json"), "user": user_map.get(p.user_id)} for p in posts]


async def summary(session: Session) -> dict:
    """当月统计：技术文章数、问答数、项目总数。"""
    start, end = _current_month_range()
    article_count = await (
        session.query(Post).filter(Post.type == "article", Post.status == "published", Post.created_at >= start, Post.created_at < end).count()
    )
    qa_count = await (
        session.query(Post).filter(Post.type == "qa", Post.status == "published", Post.created_at >= start, Post.created_at < end).count()
    )
    project_count = await project_center_service.count_projects(session)
    return {"article_count": article_count, "qa_count": qa_count, "project_count": project_count}


async def hot_articles(session: Session, top: int = _TOP_N) -> list[dict]:
    """热门文章：当月点赞数前 N 的文章。"""
    start, end = _current_month_range()
    posts = await (
        session.query(Post)
        .filter(Post.type == "article", Post.status == "published", Post.created_at >= start, Post.created_at < end)
        .order_by(col(Post.like_count).desc())
        .limit(top)
        .all()
    )
    return await _attach_authors(session, posts)


async def hot_discussions(session: Session, top: int = _TOP_N) -> list[dict]:
    """热门讨论：当月回复数前 N 的问答。"""
    start, end = _current_month_range()
    posts = await (
        session.query(Post)
        .filter(Post.type == "qa", Post.status == "published", Post.created_at >= start, Post.created_at < end)
        .order_by(col(Post.reply_count).desc())
        .limit(top)
        .all()
    )
    return await _attach_authors(session, posts)


async def hot_projects(session: Session, top: int = _TOP_N) -> list[dict]:
    """热门项目：当月点赞数前 N 的项目（按 osc_project_like 当月记录聚合）。

    只统计未软删除的项目（JOIN osc_project 过滤 is_deleted = 0），否则被删除的项目
    仍会出现在月报里、前端取标题时拿到 404。
    仅返回 project_id 与点赞数，不含项目名（前端用 GET /projects/{id} 取标题）。
    """
    start, end = _current_month_range()
    like_table = ProjectLike.table_name()
    project_table = Project.table_name()
    rows = await session.fetch_raw(
        f"SELECT l.project_id, COUNT(*) AS cnt FROM {like_table} l "
        f"JOIN {project_table} p ON p.id = l.project_id AND p.is_deleted = 0 "
        "WHERE l.created_at >= %s AND l.created_at < %s GROUP BY l.project_id ORDER BY cnt DESC LIMIT %s",
        [start, end, top],
    )
    return [{"project_id": r["project_id"], "like_count": int(r["cnt"])} for r in rows]


async def trending_topics(session: Session) -> list[dict]:
    """趋势话题：当月已发布文章的标签按归一化后的文章数量降序。"""
    start, end = _current_month_range()
    rows = await (
        session.query(Post)
        .filter(Post.type == "article", Post.status == "published", Post.created_at >= start, Post.created_at < end)
        .order_by(col(Post.id).asc())
        .select(col(Post.tags))
        .all()
    )
    return count_tags(row["tags"] for row in rows)
