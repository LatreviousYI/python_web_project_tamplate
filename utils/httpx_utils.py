# 普通请求
import httpx


limits = httpx.Limits(
    max_keepalive_connections=10,
    max_connections=20,
)

timeout = httpx.Timeout(
    connect=2.0,  # 连接超时时间
    read=120.0,  # 从开始接收响应到接收完毕的时间
    write=2.0,  # 写入超时时间
    pool=2.0,  # 从连接池中获取连接的超时时间
)

httpx_client = httpx.AsyncClient(limits=limits, timeout=timeout)


async def close_httpx():
    await httpx_client.aclose()
