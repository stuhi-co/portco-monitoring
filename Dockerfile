FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN mkdir -p src/backend && touch src/backend/__init__.py
RUN uv sync --frozen --no-dev --no-editable

COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY templates/ ./templates/
COPY src/backend/ ./src/backend/

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
