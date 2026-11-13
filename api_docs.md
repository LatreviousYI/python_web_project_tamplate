# API 文档

## 健康检查

```text
GET /sme/api/v1/health
```

响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "ok"
  }
}
```

## 统一错误响应

HTTP 状态码保留真实语义，响应体继续使用统一结构：

```json
{
  "code": 404,
  "message": "Not Found",
  "data": null
}
```
