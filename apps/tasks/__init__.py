# """
# 后台常驻任务注册

# - asyncio 常驻任务：内容审核（持续循环，空闲休眠）

# 项目中心已与云效解耦，原先每日同步云效组织成员的 cron 任务（及 apscheduler 依赖）
# 一并移除；项目创建者姓名统一由本地 osc_user 提供。
# """

# from apps.tasks.content_review import review_pending_posts_loop
# from utils import async_task


# def start_forerver_loop():
#     """启动内容审核常驻循环，返回可取消的任务。"""
#     async_task.create_task_with_safe(review_pending_posts_loop())
