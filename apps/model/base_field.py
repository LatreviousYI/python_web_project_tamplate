import datetime

from pydantic import field_serializer
from vorm import Field, Model


class BaseField(Model):
    id: int = Field(primary_key=True, auto_increment=True)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        timestamp_behavior="create",  # INSERT 时写入，UPDATE 时跳过
    )
    # MySQL → DATETIME,  PG → TIMESTAMP

    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        timestamp_behavior="both",  # INSERT / UPDATE 都会刷新
        index=True,
    )

    @field_serializer("created_at", "updated_at")
    def _serialize_datetime(self, value: datetime.datetime) -> str:
        """接口输出统一为 `YYYY-MM-DD HH:MM:SS` 格式。"""
        return value.strftime("%Y-%m-%d %H:%M:%S")
