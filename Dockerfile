# syntax=docker/dockerfile:1.7

# ============================================================================
# builder: uv で依存だけを .venv に入れる
# ----------------------------------------------------------------------------
# astral の uv 入りイメージは中身が python:3.12-slim-bookworm と同一なので、
# ここで作った /app/.venv をそのまま runtime ステージへ持っていける。
# ============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# UV_COMPILE_BYTECODE=1 : pyc を事前生成して起動を速く
# UV_LINK_MODE=copy     : キャッシュマウントを跨いでも安全なコピーリンク
# UV_PYTHON_DOWNLOADS=0 : 管理 Python を落とさずベースイメージの python を使う
#                         （venv の参照先を runtime ステージと一致させるため）
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# 依存だけ先に解決する。uv.lock / pyproject.toml が変わらない限りこの層はキャッシュされる。
# このプロジェクトは [build-system] を持たない非パッケージ構成なので --no-install-project。
# （ソースは install せず src/ から直接 import する起動形態）
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

# ============================================================================
# runtime: 依存(venv)とソースだけの薄いイメージ。uv は同梱しない。
# ============================================================================
FROM python:3.12-slim-bookworm

# 非 root ユーザーで動かす
RUN useradd --create-home --uid 1000 app

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# venv はビルドステージから、ソースはビルドコンテキストからコピー。
# pyproject.toml は resources/agents.yml の探索（親を遡って pyproject を探す）に必要なので残す。
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app src ./src
COPY --chown=app:app resources ./resources

# aibot.db と logs/ は CWD(/app) に書き込まれる。永続化は compose のボリュームで行う。
RUN mkdir -p /app/logs && chown app:app /app/logs
VOLUME ["/app/logs"]

USER app

# src は src/__init__.py を持たない namespace package。CWD=/app から module 起動する
# （ローカルの `python -m src.aibot` と同じ形態）。
# StreamHandler により stdout にもログが出るので `docker logs` / compose logs で追える。
CMD ["python", "-m", "src.aibot", "--log", "INFO"]
