# 开源社区 API 文档

> 基础路径：`/api/v1`
> 协议：HTTP/HTTPS · 数据格式：JSON（UTF-8）
> 生成日期：2026-09-14

## 目录

- [1. 通用说明](#1-通用说明)
- [2. 数据模型](#2-数据模型)
- [3. 鉴权模块 /auth](#3-鉴权模块-auth)
- [4. 首页模块 /home](#4-首页模块-home)
- [5. 内容模块 /posts](#5-内容模块-posts)
- [6. 回复模块 /replies](#6-回复模块-replies)

---

## 1. 通用说明

### 1.1 鉴权

需要登录的接口，通过 HTTP 请求头携带本地签发的 JWT：

```
Authorization: Bearer <token>
```

- Token 由 [`POST /api/v1/auth/login`](#post-authlogin) 用 SSO 票据换取，返回 `token` 字段。
- JWT payload 中的 `user_id` 为本地用户表主键 `osc_user.id`（int），路由依赖 `get_current_user` 即解出该 id。
- 未携带或非法 token 时，鉴权依赖会抛出 HTTP `401`。

### 1.2 统一响应结构

所有接口的响应体统一为：

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | int | `200` 成功；其它为业务错误码 |
| `message` | string | 提示信息 |
| `data` | any | 业务数据，可为 `null` / 对象 / 分页结构 `PageResult` |

> 说明：参数校验、鉴权、非法状态等错误通过 HTTP 状态码抛出（`400` / `401` / `403`），响应体为 FastAPI 默认的 `{"detail": "..."}`；资源不存在（如 `post not found`）由路由返回 HTTP `200`，但 `code` 为 `404`。

### 1.3 分页结构（PageResult）

列表接口统一返回 `data` 为分页结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "totals": 120,
    "data": [ /* 当前页记录 */ ]
  }
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `totals` | int | 满足条件的总记录数 |
| `data` | array | 当前页记录 |

分页查询参数（列表接口通用）：

| 参数 | 位置 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | query | int | 1 | 页码，`>= 1` |
| `page_size` | query | int | 20 | 每页条数，`1 ~ 100` |

### 1.4 状态枚举

| 枚举 | 取值 | 说明 |
| --- | --- | --- |
| 内容类型 `type` | `article` / `qa` | 文章 / 问答 |
| 内容状态 `status` | `draft` / `pending` / `published` | 草稿 / 待审核 / 已发布 |
| 投票类型 `vote_type` | `like` / `dislike` | 点赞 / 点踩 |

`status` 状态机说明：

- `draft` → `pending`：用户提交发布（用户可控）
- `pending` → `draft`：用户撤回（用户可控）
- `pending` → `published`：系统审核通过（系统控制，用户不可直接修改）
- 已 `published` 的内容，用户不能再修改状态。

---

## 2. 数据模型

### 2.1 User（`osc_user`）

SSO 用户。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键，自增 |
| `user_name` | string | 用户名 |
| `mobile` | string | 手机号 |
| `email` | string \| null | 邮箱 |
| `tenant` | string \| null | 租户 |
| `user_id` | string | SSO 账号标识（fastgo accountCode，唯一） |
| `avatar` | string \| null | 头像 URL |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

> 回复列表接口中对用户做了隐私裁剪，仅暴露 `user` 摘要：`{"id", "user_name", "avatar"}`，不含手机号 / 邮箱 / 租户。

### 2.2 Post（`osc_post`）

内容（文章 / 问答，由 `type` 区分）。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键，自增 |
| `user_id` | int | 作者用户主键 id（`osc_user.id`） |
| `type` | string | 类型：`article` / `qa` |
| `title` | string | 标题 |
| `summary` | string \| null | 摘要 |
| `content` | string | 正文（markdown） |
| `status` | string | 状态：`draft` / `pending` / `published` |
| `tags` | array | 标签列表 |
| `view_count` | int | 浏览量 |
| `like_count` | int | 点赞数 |
| `reply_count` | int | 回复数 |
| `published_at` | datetime \| null | 发布时间 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### 2.3 Reply（`osc_reply`）

统一回复（一级回复 + 二级楼中楼）。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | int | 主键，自增 |
| `user_id` | int | 回复者用户主键 id（`osc_user.id`） |
| `target_type` | string | 回复所在内容类型：`article` / `qa` |
| `target_id` | int | 回复所在内容 id（`osc_post.id`） |
| `reply_to` | int \| null | 根一级回复 id（`null` = 一级回复） |
| `reply_to_user_id` | int \| null | 被回复用户主键 id（具体 @ 了谁） |
| `content` | string | 回复内容（markdown） |
| `like_count` | int | 点赞数 |
| `dislike_count` | int | 点踩数 |
| `is_deleted` | bool | 是否已删除（软删） |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

> 回复采用扁平两级模型：`reply_to` 始终指向根一级回复；`reply_to_user_id` 记录具体被回复的用户。点赞 / 点踩除计数外，另有 `ReplyVote`（`osc_reply_vote`）记录表用于判断「当前用户是否已点赞 / 踩」。

---

## 3. 鉴权模块 /auth

### GET /auth/login-url

获取 SSO 登录地址，前端跳转。

| 鉴权 | 无 |
| --- | --- |

**请求参数（query）**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `redirect_url` | string | 是 | 登录成功后的回调地址 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": { "login_url": "https://sso.example.com/login?redirect=..." }
}
```

### POST /auth/login

用 SSO 票据（ticket）换取本地 JWT 与用户信息。

| 鉴权 | 无 |
| --- | --- |

**请求体**

```json
{ "ticket": "fastgo-ticket" }
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `ticket` | string | 是 | fastgo 单点登录票据 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "<jwt>",
    "user": {
      "id": 1,
      "user_name": "张三",
      "mobile": "13800000000",
      "email": null,
      "tenant": null,
      "user_id": "account-code",
      "avatar": null,
      "created_at": "2026-09-14 10:00:00",
      "updated_at": "2026-09-14 10:00:00"
    }
  }
}
```

---

## 4. 首页模块 /home

### GET /home/message

占位接口，返回 `"ok"`。

| 鉴权 | 无 |
| --- | --- |

**响应示例**

```
"ok"
```

---

## 5. 内容模块 /posts

### GET /posts

内容列表（文章 / 问答），按创建时间倒序。

| 鉴权 | 无 |
| --- | --- |

**请求参数（query）**

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `page` | int | 1 | 页码，`>= 1` |
| `page_size` | int | 20 | 每页条数，`1 ~ 100` |
| `type` | string | — | 可选，按类型筛选：`article` / `qa` |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "totals": 120,
    "data": [
      {
        "id": 10,
        "user_id": 1,
        "type": "article",
        "title": "标题",
        "summary": "摘要",
        "content": "# 正文 markdown",
        "status": "published",
        "tags": ["Python", "FastAPI"],
        "view_count": 100,
        "like_count": 5,
        "reply_count": 3,
        "published_at": "2026-09-14 10:00:00",
        "created_at": "2026-09-13 10:00:00",
        "updated_at": "2026-09-14 10:00:00"
      }
    ]
  }
}
```

### POST /posts

创建内容（文章 / 问答）。

| 鉴权 | 是（Bearer token） |
| --- | --- |

**请求体**

```json
{
  "title": "标题",
  "content": "# 正文 markdown",
  "type": "article",
  "status": "draft",
  "summary": "摘要",
  "tags": ["Python"]
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `title` | string | 是 | 标题，去除首尾空白后非空 |
| `content` | string | 是 | 正文，去除首尾空白后非空 |
| `type` | string | 是 | 类型：`article` / `qa` |
| `status` | string | 是 | 初始状态：`draft` / `pending` |
| `summary` | string \| null | 否 | 摘要 |
| `tags` | array | 否 | 标签列表，默认 `[]` |

**响应示例**

`data` 为创建的 [Post](#22-post-osc_post) 对象。

### GET /posts/{post_id}

内容详情（访问时 `view_count` 原子 +1）。

| 鉴权 | 无 |
| --- | --- |

**路径参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `post_id` | int | 内容 id |

**响应示例**

`data` 为 [Post](#22-post-osc_post) 对象；不存在时 `code=404`。

### PUT /posts/{post_id}

编辑内容（仅作者）。

| 鉴权 | 是（Bearer token，作者本人） |
| --- | --- |

**路径参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `post_id` | int | 内容 id |

**请求体**（均为可选，`null` 表示不更新）

```json
{ "title": "新标题", "content": "# 新正文", "summary": "新摘要", "tags": ["A", "B"] }
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `title` | string \| null | 标题 |
| `content` | string \| null | 正文 |
| `summary` | string \| null | 摘要 |
| `tags` | array \| null | 标签列表 |

**响应示例**

`data` 为更新后的 [Post](#22-post-osc_post) 对象；不存在或无权限时 `code=404`。

### DELETE /posts/{post_id}

删除内容（仅作者）。

| 鉴权 | 是（Bearer token，作者本人） |
| --- | --- |

**路径参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `post_id` | int | 内容 id |

**响应示例**

```json
{ "code": 200, "message": "success", "data": null }
```

### PATCH /posts/{post_id}/status

用户提交发布 / 撤回（`draft` ↔ `pending`）。

| 鉴权 | 是（Bearer token，作者本人） |
| --- | --- |

**路径参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `post_id` | int | 内容 id |

**请求体**

```json
{ "status": "pending" }
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | string | 是 | `draft` / `pending` |

**响应示例**

`data` 为更新后的 [Post](#22-post-osc_post) 对象。已 `published` 的内容不可由用户修改状态（HTTP `400`）。

---

## 6. 回复模块 /replies

### GET /posts/{post_id}/replies

一级回复列表（分页），每条附带其二级回复数。

| 鉴权 | 无 |
| --- | --- |

**路径参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `post_id` | int | 内容 id |

**请求参数（query）**

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `page` | int | 1 | 页码，`>= 1` |
| `page_size` | int | 20 | 每页条数，`1 ~ 100` |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "totals": 12,
    "data": [
      {
        "id": 5,
        "user_id": 1,
        "target_type": "article",
        "target_id": 10,
        "reply_to": null,
        "reply_to_user_id": null,
        "content": "一级回复内容",
        "like_count": 3,
        "dislike_count": 0,
        "is_deleted": false,
        "created_at": "2026-09-14 10:00:00",
        "updated_at": "2026-09-14 10:00:00",
        "user": { "id": 1, "user_name": "张三", "avatar": null },
        "sub_reply_count": 2
      }
    ]
  }
}
```

> 每条记录 = 回复字段 + `user`（用户摘要）+ `sub_reply_count`（二级回复数）。

### GET /replies/{reply_id}/replies

某条一级回复下的二级回复列表（分页，平级展示），附回复者与被回复者信息。

| 鉴权 | 无 |
| --- | --- |

**路径参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `reply_id` | int | 一级回复 id |

**请求参数（query）**

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `page` | int | 1 | 页码，`>= 1` |
| `page_size` | int | 20 | 每页条数，`1 ~ 100` |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "totals": 8,
    "data": [
      {
        "id": 6,
        "user_id": 2,
        "target_type": "article",
        "target_id": 10,
        "reply_to": 5,
        "reply_to_user_id": 1,
        "content": "@张三 回复你的内容",
        "like_count": 0,
        "dislike_count": 0,
        "is_deleted": false,
        "created_at": "2026-09-14 11:00:00",
        "updated_at": "2026-09-14 11:00:00",
        "user": { "id": 2, "user_name": "李四", "avatar": null },
        "reply_to_user": { "id": 1, "user_name": "张三", "avatar": null }
      }
    ]
  }
}
```

> 每条记录 = 回复字段 + `user`（回复者摘要）+ `reply_to_user`（被回复者摘要）。

### POST /posts/{post_id}/replies

发表回复（一级或二级楼中楼）。

| 鉴权 | 是（Bearer token） |
| --- | --- |

**路径参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `post_id` | int | 内容 id |

**请求体**

```json
{ "content": "回复内容", "reply_to": 5, "reply_to_user_id": 1 }
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `content` | string | 是 | 回复内容（markdown） |
| `reply_to` | int \| null | 否 | 被回复的回复 id；不传为一级回复 |
| `reply_to_user_id` | int \| null | 否 | 被回复用户 id；不传时从被回复的回复反查 |

**响应示例**

`data` 为创建的 [Reply](#23-reply-osc_reply) 对象。发表成功后内容 `reply_count` 原子 +1。

### DELETE /replies/{reply_id}

删除回复（软删，仅作者）。

| 鉴权 | 是（Bearer token，作者本人） |
| --- | --- |

**路径参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `reply_id` | int | 回复 id |

**响应示例**

```json
{ "code": 200, "message": "success", "data": null }
```

### POST /replies/{reply_id}/vote

点赞 / 点踩（切换式，`like` 与 `dislike` 互斥）。

| 鉴权 | 是（Bearer token） |
| --- | --- |

**路径参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `reply_id` | int | 回复 id |

**请求体**

```json
{ "vote_type": "like" }
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `vote_type` | string | 是 | `like` / `dislike` |

**行为说明（切换式）**

| 当前状态 | 本次操作 | 结果 |
| --- | --- | --- |
| 未点 | `like` / `dislike` | 记录 + 对应计数 `+1` |
| 已点 `like` | 再点 `like` | 取消，计数 `-1` |
| 已点 `like` | 点 `dislike` | 切换，`like_count -1`、`dislike_count +1` |

**响应示例**

`data` 为更新后的 [Reply](#23-reply-osc_reply) 对象（含最新计数）。
