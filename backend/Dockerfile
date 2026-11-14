FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY backend ./backend
COPY ml ./ml
RUN uv sync --frozen --no-dev --package backend
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app/backend
