from typing import Optional

from vorm import Field, Session
from vorm.ddl import Index

from apps.model.base_field import BaseField

# 可原子自增的计数字段（白名单，防止字段名注入）
_COUNT_FIELDS = frozenset({"like_count", "dislike_count"})


class Reply(BaseField):
    """统一回复表：文章 / 问答 下的一级回复 + 二级回复（楼中楼）。

    - 一级回复：直接回复内容本身，reply_to 为 None
    - 二级回复：回复某条一级回复，reply_to 记录被回复的回复 id
    - target_type / target_id 记录回复发生在哪类内容（平级展示时统一归属）
    """

    class Meta:
        table = "osc_reply"
        indexes = [
            Index(fields=("target_type", "target_id")),
        ]

    user_id: int = Field(index=True, comment="回复者用户主键id（osc_user.id）")
    target_type: str = Field(max_length=16, index=True, comment="回复所在内容类型: article / qa")
    target_id: int = Field(index=True, comment="回复所在内容 id")
    reply_to: Optional[int] = Field(default=None, nullable=True, comment="根一级回复id（null=一级回复）")
    reply_to_user_id: Optional[int] = Field(default=None, nullable=True, comment="被回复用户主键id（osc_user.id）")
    content: str = Field(comment="回复内容 markdown")
    like_count: int = Field(default=0, comment="点赞数")
    dislike_count: int = Field(default=0, comment="点踩数")
    is_deleted: bool = Field(default=False, comment="是否已删除")

    @classmethod
    async def incr_count(cls, session: Session, reply_id: int, field: str, amount: int = 1) -> int:
        """原子自增某个计数列（like_count / dislike_count），返回受影响行数（0 表示 reply_id 不存在）。

        计数列走白名单校验，避免字段名注入；自增在数据库端单条 UPDATE 内完成，并发下不会丢失更新。
        """
        if field not in _COUNT_FIELDS:
            raise ValueError(f"非法计数列: {field}")
        return await session.execute_raw(
            f"UPDATE {cls.table_name()} SET {field} = {field} + %s WHERE id = %s",
            [amount, reply_id],
        )


class ReplyVote(BaseField):
    """回复点赞 / 点踩记录：记录「哪个用户对哪条回复点了赞 / 踩」。

    与 Reply 上的 like_count / dislike_count（冗余计数）配套：
    - 计数用于列表展示，vote 记录用于判断「我是否已经点过赞 / 踩」
    - like 与 dislike 互斥：同一用户对同一条回复最多一条记录（reply_id + user_id 唯一）
    """

    class Meta:
        table = "osc_reply_vote"
        indexes = [
            Index(fields=("reply_id", "user_id"), unique=True),
        ]

    reply_id: int = Field(index=True, comment="回复id（osc_reply.id）")
    user_id: int = Field(index=True, comment="点赞/点踩用户主键id（osc_user.id）")
    vote_type: str = Field(max_length=16, comment="投票类型: like / dislike")
