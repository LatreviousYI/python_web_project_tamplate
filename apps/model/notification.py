import datetime
from typing import Optional

from vorm import Field
from vorm.ddl import Index

from apps.model.base_field import BaseField


class Notification(BaseField):
    """站内通知表。

    - 回复通知：有人回复了我的文章 / 问答（type=reply，actor=回复者）
    - 审核通知：我的内容审核通过 / 不通过（type=approve / reject，actor=null 表示系统）

    文章 / 问答不单独用 type 区分，post_id 关联的帖子自身知道是 article 还是 qa，
    前端跳转时自然得知；content 存摘要文案 / 审核原因。
    """

    class Meta:
        table = "osc_notification"
        indexes = [
            Index(fields=("recipient_id", "is_read")),
        ]

    recipient_id: int = Field(index=True, comment="收件人用户主键id（osc_user.id）")
    actor_id: Optional[int] = Field(default=None, index=True, nullable=True, comment="触发者用户主键id（系统通知为 null）")
    type: str = Field(max_length=16, comment="类型: reply / approve / reject")
    post_id: Optional[int] = Field(default=None, index=True, nullable=True, comment="关联内容id（osc_post.id）")
    reply_id: Optional[int] = Field(default=None, nullable=True, comment="关联回复id（reply 类型）")
    content: Optional[str] = Field(default=None, max_length=500, nullable=True, comment="摘要文案 / 审核原因")
    is_read: bool = Field(default=False, comment="是否已读")
    read_at: Optional[datetime.datetime] = Field(default=None, nullable=True, comment="已读时间")
