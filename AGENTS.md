# AI 开发约束规则（强制）

> 本文件是所有 AI 辅助开发必须遵守的强制规则。开始任何编码任务前，必须先完整阅读本文件。
> 编写涉及数据库的代码前，必须先阅读 `vorm_docs.md`（vorm 官方文档）。

## 1. 技术栈（不得擅自替换）

- Python >= 3.10，FastAPI，MySQL
- ORM：vorm（版本锁定 `vorm==0.1.9`，见 `pyproject.toml`）
- 定时任务：apscheduler（asyncio）
- 日志：nb-log（统一走 `utils/log_util.py`）
- HTTP 客户端：httpx（统一走 `utils/httpx_utils.py`）

## 2. ORM 规则（vorm）

1. **只允许使用 vorm**，禁止引入 SQLAlchemy、Tortoise、Pony、Django ORM 等任何其他 ORM。
2. **禁止使用外键**。vorm 本身不提供外键及多对一、多对多能力；表间关联一律在应用层维护：
   - 用普通整型字段保存关联表的主键 id（如 `user_id: int`），不建外键约束；
   - 需要关联数据时在 service 层显式查询或使用 vorm 的 JOIN（显式 ON 条件）。
3. **主键规则**：单数据库场景下，主键统一使用自增 int id。所有模型必须继承 `apps/model/base_field.py` 的 `BaseField`（已内置 `id` 自增主键、`created_at`、`updated_at`），业务模型不得重复定义这三个字段。
4. 模型必须通过 `class Meta` 指定 `table` 表名；需要唯一约束时用 `Meta.indexes` 声明 `Index(fields=(...), unique=True)`。
5. 建表 / 同步表结构使用 `Model.sync_table()`（只增改不删），统一在 `factory/bootstrap.py` 的 `init_db()` 中注册。
6. 数据库会话获取方式（见 `common/db.py`）：
   - 路由层：`session = Depends(get_session)`；
   - 非请求上下文（任务、后台逻辑）：`async with get_asynccontext_session() as session:`。
   - 禁止在引擎 / 会话管理之外自行创建连接。

## 3. 项目结构（大结构不得变动）

严格按现有目录分层开发，禁止新建顶层目录、禁止移动 / 重命名现有目录：

```
apps/
├── model/      # vorm ORM 模型定义（继承 BaseField）
├── router/     # 路由层：参数校验、调用 service、返回 ApiResponse，保持薄
├── service/    # 业务逻辑层：所有数据库操作都在这里完成
└── tasks/      # 定时任务 / 后台任务
common/         # 公共基础设施（db 引擎与会话）
configs/        # 多环境配置（dev / test / uat / prod，按 APP_ENV 切换）
factory/        # 应用工厂（main.py、middleware.py、bootstrap.py 启动引导）
utils/          # 通用工具（日志、响应、httpx、jwt、excel、异步任务等）
```

分层纪律：

- router 不直接操作数据库，必须调用 service；
- service 不处理 HTTP 细节，业务错误用 `utils/response_utils.py` 的 `abort()` 等函数抛出；
- 配置一律从 `configs.settings` 读取，禁止硬编码环境相关值；
- 接口响应统一返回 `ApiResponse` / `PageResult`（`utils/response_utils.py`）；
- 新路由在 `factory/main.py` 的 `register_routers()` 中挂载到 `api_router`；
- 启动任务统一注册：数据库连接池、定时任务、持久任务全部在 `factory/bootstrap.py` 中注册（`init_db()` / `register_schedulers()` / `register_forever_tasks()`），`factory/main.py` 的 lifespan 只调用 `bootstrap.startup()` / `bootstrap.shutdown()`，禁止在 main.py 中直接注册任务。

## 4. 配置管理（configs/）

配置采用纯 Python 类属性风格（非 pydantic-settings、非 yaml / .env 配置文件），结构固定：

- `configs/base_conf.py` — `BaseSettings` 基类：所有环境共享的配置（`app_name`、`basedir`、jwt 相关、`background_tasks` 等），带默认值和注释；
- `configs/dev_conf.py` / `test_conf.py` / `uat_conf.py` / `prod_conf.py` — 各环境配置类，继承 `BaseSettings`，定义 `env` 环境标识 + 仅该环境的差异项（`db_host`、`db_port`、`db_user`、`db_pass`、`db_name` 等）；
- `configs/__init__.py` — 环境映射字典 `config` + `get_settings()`（`@lru_cache()` 进程内单例）：按 `APP_ENV` 选择配置类实例化、注入 `SEC_KEY`，导出全局 `settings`。

新增配置项规则：

1. 各环境相同的配置：加到 `BaseSettings`（默认值 + 用途注释）；
2. 仅个别环境不同的配置：`BaseSettings` 给默认值，对应环境类中覆盖；
3. 新增环境：新建 `xxx_conf.py` 继承 `BaseSettings`，并在 `configs/__init__.py` 的 `config` 字典注册。

使用规则：

- 读取配置统一 `from configs import settings`（或 `import configs` 后 `configs.settings.xxx`）；
- 环境变量只在 `configs/__init__.py` 的 `get_settings()` 中读取（仅 `APP_ENV`、`SEC_KEY` 两个），业务代码禁止直接 `os.getenv` / `os.environ`；
- 敏感配置（如 `db_pass`）必须密文存储，经 `utils/cipher_util.py` 解密后使用（`SEC_KEY` 由环境变量注入），禁止明文密码写入代码；
- `settings` 为 `lru_cache` 单例，禁止在运行期修改配置对象属性。

## 5. 异步优先

1. 所有 I/O（数据库、HTTP、文件读写）必须使用 `async` / `await`。
2. 禁止在事件循环中使用阻塞调用：
   - 禁止 `requests`、`time.sleep()`、同步文件读写、同步 DB 驱动；
   - 用 `httpx.AsyncClient`（`utils/httpx_utils.py`）、`asyncio.sleep()`、`aiofiles`。
3. **后台/持久任务必须用 `utils/async_task.py` 的 `create_task_with_safe(coro)` 创建**（自动加入 `settings.background_tasks` 托管集合，任务完成自动移除，应用关闭时统一等待收尾），禁止裸用 `asyncio.create_task()`。传入的是**协程对象**（调用 async 函数的返回值），不是函数本身：

   ```python
   # 正确：传入协程对象
   create_task_with_safe(send_email())
   create_task_with_safe(send_email(user_id="123"))

   # 错误：传入函数本身
   create_task_with_safe(send_email)
   ```

4. 持久任务（forever loop）标准写法：`while` 循环内每轮检查 `configs.settings.background_tasks_shutdown_stauts`，为 `1` 时退出循环，保证应用关闭时 `shutdown_forever_task()` 能等待收尾：

   ```python
   async def my_forever_loop():
       while configs.settings.background_tasks_shutdown_stauts == 0:
           ...  # 业务逻辑
           await asyncio.sleep(5)
   ```

5. 路由处理函数一律 `async def`。

## 6. 通用工具使用规范（utils/）

写新代码前先查 `utils/` 是否已有现成实现，禁止重复造轮子；新的通用函数也放 `utils/` 对应模块（按现有文件归类，不新建碎片文件）：

- **日志**：统一 `log_util.logger`（nb_log，自动落盘），禁止 `print()` 调试输出、禁止自行 `import logging` 配置；
- **HTTP 请求**：统一用 `httpx_utils.httpx_client`（全局单例，已预配置超时与连接池上限），禁止每次请求新建 `httpx.AsyncClient`、禁止 `requests`；
- **JWT / 鉴权**：生成 token 用 `jwt.generate_token(data)`；路由鉴权用依赖 `jwt.verify_token`（返回 user_id，未登录 401）或 `jwt.verify_token_optional`（可选鉴权，未登录返回 None），禁止在业务代码中自行 decode / 校验 token；
- **加解密**：统一 `cipher_util.cipher.encrypt()` / `decrypt()`（AES，密钥为环境变量注入的 `SEC_KEY`），禁止自行实现加解密逻辑；
- **JSON 序列化**：统一 orjson：`tools.dict_to_json` / `dict_to_json_ea` / `json_to_dict`（自动处理 datetime / Decimal / bytes），禁止 `json.dumps` 序列化含 datetime 的数据；
- **日期时间**：对外输出统一 `YYYY-MM-DD HH:MM:SS`（`tools.datetime_to_string()`）；解析外部时间字符串用 `tools.parse_datetime()`（多格式容错），禁止手写 `strptime` 硬编码单一格式；
- **请求体解析**：POST JSON body 解析为 dict 用依赖 `request_utils.GetPostJsonBody`；
- **重试**：异步重试用装饰器 `tools.async_retry_on_error(max_attempts, delay)`；
- **入库清洗**：外部输入入库前用 `tools.sanitize_for_db()` 清洗非法控制字符；
- **CSV 导出**：Excel 兼容的 CSV 流导出用 `excel_util.write_stream()`（utf-8-sig 带 BOM）；
- **数值计算**：分母可能为 0 的除法用 `calculate.division()`（返回 0 不抛错），环比计算用 `calculate.calculate_ring_ratio()`。

## 7. 环境管理（uv）

1. 本地开发统一使用 uv 管理 Python 环境：
   - 安装依赖：`uv sync`；
   - 新增依赖：`uv add <package>`（写入 `pyproject.toml` 并更新 `uv.lock`）；
   - 运行：`uv run <command>`。
2. 禁止直接 `pip install`（会绕过 lock，导致环境不可复现）。
3. `pyproject.toml` 和 `uv.lock` 必须保持同步提交。

## 8. 部署形态与分布式锁（重要）

1. 生产环境使用 gunicorn + `uvicorn.workers.UvicornWorker` 启动**多个 worker**（数量 = CPU 核数，见 `gunicorn.conf.py`；dev/uat 为 2 个）。因此：
   - **进程内存不共享**：模块级变量、内存缓存、单例状态在每个 worker 中各有一份，禁止当作全局共享存储使用；
   - **任何"只应执行一次"的逻辑都会被每个 worker 各执行一次**。
2. 定时任务（apscheduler）必须加**分布式锁**，防止多 worker 重复触发、重复执行。
3. 涉及互斥的资源（任务调度、缓存重建、唯一性写入等）必须使用分布式锁方案（如数据库锁表 / 唯一索引抢占、Redis 锁等），禁止依赖进程内锁（`threading.Lock` 等对多 worker 无效）。
4. vorm 提供 `for_update()` / `for_update(skip_locked=True)` 行级悲观锁，仅可在事务内使用；跨 worker 的调度互斥优先用"锁表 + 唯一索引抢占"模式。

## 9. 代码风格

- ruff 检查（`pyproject.toml` 已配置）：行宽 150、4 空格缩进、双引号；
- 新增代码必须通过 ruff 检查，不留 `F401`（未使用导入）、`F821`（未定义名称）等错误。

## 10. 禁止事项速查

- 禁止引入 vorm 之外的 ORM 或数据库访问方式（原生 SQL 仅在必要时用 vorm 的 `execute_raw()` / `fetch_raw()`）；
- 禁止外键、多对多 ORM 关系；
- 禁止改动 `factory/`、`common/`、`configs/` 的现有结构与启动流程（除非任务明确要求）；
- 禁止同步阻塞调用；
- 禁止直接 pip 安装依赖；
- 禁止在业务代码中直接读取环境变量（`os.getenv` / `os.environ`）或硬编码配置，配置一律走 `configs.settings`；
- 禁止 `print()` 调试输出，日志统一 `log_util.logger`；
- 禁止重复造轮子：写工具函数前先查 `utils/` 是否已有实现；
- 禁止绕过 `BaseField` 自行定义主键为非自增 int（单库场景）；
- 禁止假设单 worker 运行而省略分布式锁。
