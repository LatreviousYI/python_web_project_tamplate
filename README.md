阿里云效令牌过期创建
https://account-devops.aliyun.com/settings/personalAccessToken

令牌过期后需要获取新的令牌保存到数据库中
表名 osc_kv
key=ali_yunxiao_token
value = utils\cipher_util.py.cipher.encrypt(明文)

文章 / 问答正文最多支持 25000 个 Unicode 字符（含 Markdown 标记，忽略首尾空白）。
`osc_post.content` 使用 `MEDIUMTEXT`，避免汉字超过原 `TEXT` 的 65535 字节容量。
部署后需重启后端：启动流程的 `sync_db()` 会自动将现有正文列从 `TEXT` 扩展为 `MEDIUMTEXT`，保留已有内容。


```bash
导出包列表到requirements.txt
uv pip compile --emit-index-url --universal pyproject.toml -o requirements.txt
```
