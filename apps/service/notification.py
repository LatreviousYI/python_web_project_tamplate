"""
通知业务层

负责站内通知的写入、列表（含触发者 / 帖子标题富化）、单条已读、全部已读、未读数。

通知写入采用 best-effort：调用方自行 try/except，失败不影响主流程（回复 / 审核）。
"""

import datetime
from typing import Optional

from vorm import Session, col

from apps.model.auth import User
from apps.model.notification import Notification
from apps.model.post import Post


def _user_summary(user: User) -> dict:
    """通知列表里触发者的最小用户信息（不泄露手机号 / 邮箱 / 租户）。"""
    return {"id": user.id, "user_name": user.user_name, "name": user.name, "avatar": user.avatar}


async def create_notification(
    session: Session,
    recipient_id: int,
    type: str,
    actor_id: Optional[int] = None,
    post_id: Optional[int] = None,
    reply_id: Optional[int] = None,
    content: Optional[str] = None,
) -> Notification | None:
    """写一条通知；自己给自己操作（actor == recipient）时不产生通知。"""
    if actor_id is not None and actor_id == recipient_id:
        return None
    notification = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        type=type,
        post_id=post_id,
        reply_id=reply_id,
        content=content,
    )
    await session.save(notification)
    return notification


async def list_notifications(
    session: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    unread_only: Optional[bool] = None,
) -> dict:
    """当前用户的通知列表（分页），附触发者信息与帖子标题。"""
    query = session.query(Notification).filter(Notification.recipient_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read == False)  # noqa: E712
    totals = await query.count()
    notifications = await query.order_by(col(Notification.id).desc()).offset((page - 1) * page_size).limit(page_size).all()
    if not notifications:
        return {"totals": totals, "data": []}

    actor_ids = {n.actor_id for n in notifications if n.actor_id is not None}
    post_ids = {n.post_id for n in notifications if n.post_id is not None}
    actor_map = await _user_map(session, actor_ids)
    post_title_map = await _post_title_map(session, post_ids)

    data = [
        {
            **n.model_dump(mode="json"),
            "actor": actor_map.get(n.actor_id) if n.actor_id is not None else None,
            "post_title": post_title_map.get(n.post_id) if n.post_id is not None else None,
        }
        for n in notifications
    ]
    return {"totals": totals, "data": data}


async def _user_map(session: Session, user_ids: set[int]) -> dict[int, dict]:
    """批量查询触发者最小信息。"""
    if not user_ids:
        return {}
    users = await session.query(User).filter(col(User.id).in_(user_ids)).all()
    return {u.id: _user_summary(u) for u in users}


async def _post_title_map(session: Session, post_ids: set[int]) -> dict[int, str]:
    """批量查询关联帖子标题（帖子可能已删，缺省返回 None）。"""
    if not post_ids:
        return {}
    posts = await session.query(Post).filter(col(Post.id).in_(post_ids)).all()
    return {p.id: p.title for p in posts}


async def mark_read(session: Session, user_id: int, notification_id: int) -> bool:
    """单条已读（仅本人可见可读），返回是否命中。"""
    notification = (
        await session.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_id == user_id,
        )
        .first()
    )
    if notification is None:
        return False
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.datetime.now()
        await session.save(notification)
    return True


async def mark_all_read(session: Session, user_id: int) -> int:
    """全部已读，返回受影响行数。"""
    return await session.execute_raw(
        f"UPDATE {Notification.table_name()} SET is_read = 1, read_at = %s WHERE recipient_id = %s AND is_read = 0",
        [datetime.datetime.now(), user_id],
    )


async def delete_notification(session: Session, user_id: int, notification_id: int) -> bool:
    """删除当前用户的一条通知，返回是否命中。"""
    notification = (
        await session.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_id == user_id,
        )
        .first()
    )
    if notification is None:
        return False
    await session.delete(notification)
    return True


async def delete_all_read(session: Session, user_id: int) -> int:
    """删除当前用户的全部已读通知，返回受影响行数。"""
    return await session.execute_raw(
        f"DELETE FROM {Notification.table_name()} WHERE recipient_id = %s AND is_read = 1",
        [user_id],
    )


async def unread_count(session: Session, user_id: int) -> int:
    """当前用户未读数量。"""
    return (
        await session.query(Notification)
        .filter(
            Notification.recipient_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
        .count()
    )
