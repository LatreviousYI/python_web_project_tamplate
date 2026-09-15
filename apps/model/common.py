import datetime
from typing import Optional

from vorm import Field
from vorm.ddl import Index

from apps.model.base_field import BaseField


class KeyValue(BaseField):
    """通用 key-value 存储表。

    用于缓存、功能开关、零散配置等键值数据；value 存 JSON 字符串，读时按需反序列化。
    expire_at 非空表示该键有过期时间，读取时做惰性过期判定（配合定时清理）。
    """

    class Meta:
        table = "osc_kv"
        indexes = [
            Index(fields=("key",), unique=True),
            Index(fields=("expire_at",)),
        ]

    key: str = Field(max_length=200, comment="键（唯一）")
    value: str = Field(comment="值（JSON 字符串 / 纯文本）")
    expire_at: Optional[datetime.datetime] = Field(default=None, nullable=True, comment="过期时间（null=永不过期）")
    remark: Optional[str] = Field(default=None, max_length=500, nullable=True, comment="备注")


class DistributedLock(BaseField):
    """分布式锁表。

    以 lock_key 唯一约束保证互斥：
    - 加锁 = INSERT（唯一冲突即加锁失败）
    - 解锁 = 按 lock_key + owner 条件 DELETE（校验持有者，避免误删他人锁）
    - expire_at 为租约到期时间，超时视为锁已自动释放（可被抢占）

    created_at 即加锁时间，updated_at 可作续租（heartbeat）刷新。
    """

    class Meta:
        table = "osc_distributed_lock"
        indexes = [
            Index(fields=("lock_key",), unique=True),
            Index(fields=("expire_at",)),
        ]

    lock_key: str = Field(max_length=200, comment="锁标识（唯一）")
    owner: str = Field(max_length=200, comment="持锁者标识（节点 / 请求 id）")
    expire_at: datetime.datetime = Field(comment="锁过期时间（租约到期）")
