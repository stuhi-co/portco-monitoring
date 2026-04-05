#!/usr/bin/env bash
set -e

# ── Stuhi Portfolio Intelligence — one-command launcher ──────────────────────
#
# Usage:  ./start.sh          (Docker — runs everything in containers)
#         ./start.sh local    (local dev — requires uv + pnpm + Docker for DB)

MODE="${1:-docker}"

# Source .env so Postgres vars are available to this script
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

PG_USER="${POSTGRES_USER:-portco}"
PG_DB="${POSTGRES_DB:-portco_monitoring}"

if [ "$MODE" = "local" ]; then
  echo "==> Starting database..."
  docker compose up -d db

  echo "==> Waiting for Postgres to be ready..."
  until docker compose exec db pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; do
    sleep 1
  done

  echo "==> Running migrations..."
  uv run alembic upgrade head

  echo "==> Starting backend (port 8000) and frontend (port 3000)..."
  trap 'kill 0' EXIT
  uv run uvicorn backend.main:app --reload --port 8000 &
  (cd src/frontend && pnpm dev) &

  echo ""
  echo "  Backend:   http://localhost:8000"
  echo "  Frontend:  http://localhost:3000"
  echo ""
  echo "  Press Ctrl+C to stop everything."
  echo ""

  wait
else
  echo "==> Building and starting all services..."
  docker compose up --build -d

  echo "==> Waiting for backend to be ready..."
  until docker compose exec backend curl -sf http://localhost:8000/api/health >/dev/null 2>&1; do
    sleep 2
  done

  echo "==> Running migrations..."
  docker compose exec backend uv run alembic upgrade head

  echo ""
  echo "  App is running at http://localhost:3000"
  echo ""
  echo "  View logs:   docker compose logs -f"
  echo "  Stop:        docker compose down"
  echo ""
fi
