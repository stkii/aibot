# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# 依存だけを先にインストールし、ビルド間でキャッシュする。
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim-bookworm

RUN useradd --create-home --uid 1000 app

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /app/.venv /app/.venv
# agents.yml の探索に使うため、pyproject.toml も配置する。
COPY pyproject.toml ./
COPY src ./src
COPY resources ./resources

# DB・SQLiteの補助ファイル・ログをまとめて保存する。
RUN mkdir -p /app/data/logs && chown -R app:app /app/data
VOLUME ["/app/data"]
WORKDIR /app/data

USER app
CMD ["python", "-m", "src.aibot", "--log", "INFO"]
