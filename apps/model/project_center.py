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


class ProjectLike(BaseField):
    """项目点赞记录：记录「哪个用户赞了哪个项目（云效仓库）」。

    项目本身不落库（实时透传云效），点赞记录存本地，用于「点赞数」与「是否已赞」判断。
    同一用户对同一项目最多一条记录（project_id + user_id 唯一）。
    """

    class Meta:
        table = "osc_project_like"
        indexes = [
            Index(fields=("project_id", "user_id"), unique=True),
        ]

    project_id: int = Field(index=True, comment="项目id（云效仓库id）")
    user_id: int = Field(index=True, comment="点赞用户主键id（osc_user.id）")
