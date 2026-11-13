# Python Web Project Template

基于 FastAPI、vorm 和 MySQL 的基础项目模板。

## 本地启动

安装依赖：

```bash
uv sync
```

复制环境变量示例并生成 `SEC_KEY`：

```bash
cp .env.example .env
chmod 600 .env
uv run python -c "from utils.cipher_util import generate_sec_key; print(generate_sec_key())"
```

将生成结果写入 `.env`：

```text
APP_ENV=dev
SEC_KEY=生成的64位十六进制字符串
```

在 `configs/dev_conf.py` 配置数据库连接。`db_pass` 必须是密文：

```bash
uv run python -c "from utils.cipher_util import cipher; print(cipher.encrypt('数据库密码'))"
```

启动服务：

```bash
uv run python start.py
```

健康检查：

```text
GET http://127.0.0.1:8779/sme/api/v1/health
```

## Docker

Docker 构建只使用 `uv.lock`，根目录 `.env` 不会进入镜像。生产环境通过环境变量或只读挂载注入 `.env`：

```bash
docker build -t python-web-template .
docker run --rm --env-file .env -p 8779:8779 python-web-template
```

## requirements.txt

`requirements.txt` 是由 lock 文件生成的部署辅助文件，不作为本地安装入口：

```bash
uv export --frozen --no-hashes --format requirements-txt -o requirements.txt
```
