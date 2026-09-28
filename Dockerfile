# syntax=docker/dockerfile:1
FROM python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /bin/

WORKDIR /code

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/code/.venv \
    PATH="/code/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Install deps first for better layer caching (app code copied later)
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project --all-groups

COPY ./app /code/app
RUN mkdir -p /code/data

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--port", "8000", "--host", "0.0.0.0"]
