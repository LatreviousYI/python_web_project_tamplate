from vorm import Field
from vorm.ddl import Index

from apps.model.base_field import BaseField


class YunxiaoUser(BaseField):
    """阿里云效组织成员（定时同步，只存 userId + name）。

    用于后续代码仓库列表中 creatorUid → 姓名 的展示匹配。
    """

    class Meta:
        table = "osc_yunxiao_user"
        indexes = [
            Index(fields=("user_id",), unique=True),
        ]

    user_id: str = Field(max_length=200, comment="云效 userId（对应仓库 creatorUid）")
    name: str = Field(max_length=100, comment="姓名")
