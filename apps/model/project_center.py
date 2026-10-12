from typing import Optional

from vorm import Field
from vorm.ddl import Index

from apps.model.base_field import BaseField


class Project(BaseField):
    """社区项目（本地落库）。

    项目元信息完全以本地库为准，已与云效仓库解耦：标题 / 标签为必填，
    简介、仓库链接为选填（链接仅作为字符串保存，不做可用性校验、不绑定任何云效仓库）。

    删除采用软删除：``is_deleted`` 置 1 即可，项目行与项目下的内容（文章 / 问答 /
    回复 / 点赞 / 贡献者）全部保留，列表与详情不再返回该项目。
    """

    class Meta:
        table = "osc_project"
        indexes = [
            # 列表固定按 is_deleted 过滤 + created_at 倒序，联合索引可直接覆盖
            Index(fields=("is_deleted", "created_at")),
        ]

    user_id: int = Field(index=True, comment="创建者用户主键id（osc_user.id）")
    title: str = Field(max_length=200, comment="项目标题")
    summary: Optional[str] = Field(default=None, nullable=True, comment="项目简介（Markdown 正文，TEXT）")
    tags: list = Field(default_factory=list, comment="标签列表")
    repo_url: Optional[str] = Field(default=None, max_length=500, nullable=True, comment="仓库链接（选填，可后期补充）")
    is_deleted: bool = Field(default=False, comment="是否已软删除（1=已删除，不再出现在列表/详情）")


class ProjectContributor(BaseField):
    """项目贡献者：记录「哪个注册用户是哪个项目的贡献者」。

    贡献者来源于 osc_user 中已注册用户，一个项目可有多名贡献者，
    同一用户对同一项目最多一条记录（project_id + user_id 唯一）。
    user_id 单独建索引，便于按用户 id 反查其参与的项目。
    """

    class Meta:
        table = "osc_project_contributor"
        indexes = [
            Index(fields=("project_id", "user_id"), unique=True),
        ]

    project_id: int = Field(index=True, comment="项目id（osc_project.id）")
    user_id: int = Field(index=True, comment="贡献者用户主键id（osc_user.id）")


class ProjectLike(BaseField):
    """项目点赞记录：记录「哪个用户赞了哪个项目」。

    点赞记录存本地，用于「点赞数」与「是否已赞」判断。
    同一用户对同一项目最多一条记录（project_id + user_id 唯一）。
    """

    class Meta:
        table = "osc_project_like"
        indexes = [
            Index(fields=("project_id", "user_id"), unique=True),
        ]

    project_id: int = Field(index=True, comment="项目id（osc_project.id）")
    user_id: int = Field(index=True, comment="点赞用户主键id（osc_user.id）")
