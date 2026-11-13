FROM ghcr.io/astral-sh/uv:0.10.9 AS uv

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    TZ=Asia/Shanghai

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app

COPY --chown=app:app . .
RUN uv sync --frozen --no-dev
RUN mkdir -p /app/logs \
    && chown -R app:app /app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8779

USER app

CMD ["gunicorn", "-c", "gunicorn.conf.py"]
