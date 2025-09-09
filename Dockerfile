# --- Builder Stage ---
# This stage installs dependencies and builds the application.
FROM python:3.12-slim AS builder

# Install uv from the latest distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency definitions first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies only (without the project itself) for optimal layer caching
# This layer will be cached unless dependencies change
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable --compile-bytecode

# Copy the application source code
ADD . /app

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --compile-bytecode

# --- Runtime Stage ---
# This stage creates the final, lean image.
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy the application source code
COPY --from=builder /app/src /app/src

# Create non-root user for security
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --create-home app

USER app

# Command to run the application using the virtual environment's Python
CMD ["/app/.venv/bin/python", "-m", "src.aibot"]
