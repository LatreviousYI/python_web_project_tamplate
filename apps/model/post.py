import datetime
from typing import Optional

from pydantic import field_serializer
from vorm import Field, Session
from vorm.ddl import Index

from apps.model.base_field import BaseField

# 可原子自增的计数字段（白名单，防止字段名注入）
_COUNT_FIELDS = frozenset({"view_count", "reply_count", "like_count"})


class Post(BaseField):
    """统一内容表：文章 / 问答（由 type 区分）。"""

    class Meta:
        table = "osc_post"

    user_id: int = Field(index=True, comment="作者用户主键id（osc_user.id）")
    project_id: Optional[int] = Field(default=None, index=True, nullable=True, comment="关联项目id（osc_project.id，可空）")
    type: str = Field(max_length=16, comment="类型: article / qa")
    title: str = Field(max_length=200, comment="标题")
    summary: Optional[str] = Field(default=None, max_length=500, nullable=True, comment="摘要")
    content: str = Field(comment="正文 markdown")
    status: str = Field(max_length=16, default="draft", comment="状态: draft(草稿) / pending(待审核) / published(已发布)")
    tags: list = Field(default_factory=list, comment="标签列表")
    view_count: int = Field(default=0, comment="浏览量")
    like_count: int = Field(default=0, comment="点赞数")
    reply_count: int = Field(default=0, comment="回复数")
    published_at: Optional[datetime.datetime] = Field(default=None, nullable=True, comment="发布时间")

    @field_serializer("published_at")
    def _serialize_published_at(self, value: Optional[datetime.datetime]) -> Optional[str]:
        return value.strftime("%Y-%m-%d %H:%M:%S") if value else None

    @classmethod
    async def incr_count(cls, session: Session, post_id: int, field: str, amount: int = 1) -> int:
        """原子自增某个计数列（view_count / reply_count / like_count），返回受影响行数（0 表示 post_id 不存在）。

        计数列走白名单校验，避免字段名注入；自增在数据库端单条 UPDATE 内完成，并发下不会丢失更新。
        """
        if field not in _COUNT_FIELDS:
            raise ValueError(f"非法计数列: {field}")
        return await session.execute_raw(
            f"UPDATE {cls.table_name()} SET {field} = {field} + %s WHERE id = %s",
            [amount, post_id],
        )


class PostLike(BaseField):
    """文章 / 问答点赞记录：记录「哪个用户赞了哪篇内容」，用于判断是否已赞、支持取消。

    与 Post 上的 like_count（冗余计数）配套：
    - 计数用于列表展示，like 记录用于判断「我是否已经点过赞」
    - 同一用户对同一内容最多一条记录（post_id + user_id 唯一）
    """

    class Meta:
        table = "osc_post_like"
        indexes = [
            Index(fields=("post_id", "user_id"), unique=True),
        ]

    post_id: int = Field(index=True, comment="内容id（osc_post.id）")
    user_id: int = Field(index=True, comment="点赞用户主键id（osc_user.id）")
