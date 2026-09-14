"""
回复业务层

负责文章 / 问答 下统一回复（一级回复 + 二级回复）的查询与增删。
回复的 target_type 由所属 Post.type 派生并冗余存储，方便平级展示与统计。

两个列表接口：
- list_first_level_replies: 一级回复（直接回复内容），附每条的二级回复数
- list_sub_replies: 某条一级回复下的所有二级回复（平级展示，附回复者与被回复者信息）
"""

from typing import Optional

from vorm import Session, col

from apps.model.auth import User
from apps.model.post import Post
from apps.model.reply import Reply, ReplyVote
from utils.response_utils import abort


def _user_summary(user: User) -> dict:
    """回复列表里暴露的最小用户信息（不泄露手机号 / 邮箱 / 租户）。"""
    return {"id": user.id, "user_name": user.user_name, "avatar": user.avatar}


async def list_first_level_replies(
    session: Session,
    post_id: int,
    page: int = 1,
    page_size: int = 20,
) -> dict | None:
    """一级回复列表：直接回复内容本身（reply_to 为 null），附每条的二级回复数。"""
    post = await session.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return None
    query = session.query(Reply).filter(
        Reply.target_type == post.type,
        Reply.target_id == post_id,
        col(Reply.reply_to).is_null(),
        Reply.is_deleted == False,  # noqa: E712
    )
    totals = await query.count()
    replies = await query.order_by(col(Reply.id).asc()).offset((page - 1) * page_size).limit(page_size).all()
    if not replies:
        return {"totals": totals, "data": []}

    user_ids = {r.user_id for r in replies}
    users = await session.query(User).filter(col(User.id).in_(user_ids)).all()
    user_map = {u.id: u for u in users}

    sub_count_map = await _count_sub_replies(session, [r.id for r in replies])

    data = [
        {
            **r.model_dump(mode="json"),
            "user": _user_summary(user_map[r.user_id]) if r.user_id in user_map else None,
            "sub_reply_count": sub_count_map.get(r.id, 0),
        }
        for r in replies
    ]
    return {"totals": totals, "data": data}


async def _count_sub_replies(session: Session, reply_ids: list[int]) -> dict[int, int]:
    """统计每条一级回复下的二级回复数（单条 GROUP BY，避免 N+1 查询）。"""
    if not reply_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(reply_ids))
    rows = await session.fetch_raw(
        f"SELECT reply_to, COUNT(*) AS cnt FROM {Reply.table_name()} WHERE reply_to IN ({placeholders}) AND is_deleted = 0 GROUP BY reply_to",
        reply_ids,
    )
    return {row["reply_to"]: int(row["cnt"]) for row in rows}


async def list_sub_replies(
    session: Session,
    reply_id: int,
    page: int = 1,
    page_size: int = 20,
) -> dict | None:
    """某条一级回复下的二级回复（分页，平级展示，附回复者与被回复者信息）。"""
    parent = await session.query(Reply).filter(Reply.id == reply_id).first()
    if parent is None:
        return None
    query = session.query(Reply).filter(
        Reply.reply_to == reply_id,
        Reply.is_deleted == False,  # noqa: E712
    )
    totals = await query.count()
    replies = await query.order_by(col(Reply.id).asc()).offset((page - 1) * page_size).limit(page_size).all()
    if not replies:
        return {"totals": totals, "data": []}

    user_ids: set[int] = set()
    for r in replies:
        user_ids.add(r.user_id)
        if r.reply_to_user_id is not None:
            user_ids.add(r.reply_to_user_id)
    users = await session.query(User).filter(col(User.id).in_(user_ids)).all()
    user_map = {u.id: u for u in users}

    data = []
    for r in replies:
        item = {
            **r.model_dump(mode="json"),
            "user": _user_summary(user_map[r.user_id]) if r.user_id in user_map else None,
            "reply_to_user": (
                _user_summary(user_map[r.reply_to_user_id]) if r.reply_to_user_id is not None and r.reply_to_user_id in user_map else None
            ),
        }
        data.append(item)
    return {"totals": totals, "data": data}


async def create_reply(
    session: Session,
    post_id: int,
    user_id: int,
    content: str,
    reply_to: Optional[int] = None,
    reply_to_user_id: Optional[int] = None,
) -> Reply | None:
    post = await session.query(Post).filter(Post.id == post_id).first()
    if post is None:
        return None
    # 二级回复：把 reply_to 归一化到根一级回复，保证扁平两级展示；
    # reply_to_user_id 记录「具体 @ 了谁」，未显式传时从被回复的回复反查。
    if reply_to is not None:
        parent = await session.query(Reply).filter(Reply.id == reply_to).first()
        if parent is None:
            abort(400, "被回复的回复不存在")
        # parent 本身是一级回复则用其 id，否则取其 reply_to（即根一级回复）
        reply_to = reply_to if parent.reply_to is None else parent.reply_to
        if reply_to_user_id is None:
            reply_to_user_id = parent.user_id
    reply = Reply(
        user_id=user_id,
        target_type=post.type,
        target_id=post_id,
        content=content,
        reply_to=reply_to,
        reply_to_user_id=reply_to_user_id,
    )
    await session.save(reply)
    # 回写内容回复数：原子自增（model 层统一封装）
    await Post.incr_count(session, post_id, "reply_count")
    return reply


async def delete_reply(session: Session, reply_id: int, user_id: int) -> Reply | None:
    reply = await session.query(Reply).filter(Reply.id == reply_id, Reply.user_id == user_id).first()
    if reply is None:
        return None
    reply.is_deleted = True
    await session.save(reply)
    return reply


async def vote_reply(
    session: Session,
    reply_id: int,
    user_id: int,
    vote_type: str,
) -> Reply | None:
    """点赞 / 点踩（切换式，like 与 dislike 互斥）：
    - 首次点 → 插入记录 + 对应计数 +1
    - 重复点同一个 → 取消：删记录 + 计数 -1
    - 点相反 → 切换：旧计数 -1、新计数 +1

    返回最新回复（含最新计数）；reply_id 不存在时返回 None。
    """
    if vote_type not in ("like", "dislike"):
        abort(400, "vote_type 必须是 like 或 dislike")
    reply = await session.query(Reply).filter(Reply.id == reply_id).first()
    if reply is None:
        return None

    existing = await session.query(ReplyVote).filter(ReplyVote.reply_id == reply_id, ReplyVote.user_id == user_id).first()

    if existing is None:
        # 首次点：插入记录 + 对应计数 +1
        await session.save(ReplyVote(reply_id=reply_id, user_id=user_id, vote_type=vote_type))
        await Reply.incr_count(session, reply_id, f"{vote_type}_count", 1)
    elif existing.vote_type == vote_type:
        # 重复点同一个 → 取消：删记录 + 计数 -1
        await session.delete(existing)
        await Reply.incr_count(session, reply_id, f"{vote_type}_count", -1)
    else:
        # 切换：改记录 + 旧计数 -1、新计数 +1
        existing.vote_type = vote_type
        await session.save(existing)
        other = "dislike" if vote_type == "like" else "like"
        await Reply.incr_count(session, reply_id, f"{other}_count", -1)
        await Reply.incr_count(session, reply_id, f"{vote_type}_count", 1)

    return await session.query(Reply).filter(Reply.id == reply_id).first()
