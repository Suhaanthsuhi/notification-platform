#!/usr/bin/env bash
#
# setup.sh — Local development setup for notifty (notification platform)
#
# A distributed, event-driven notification system built on Redis Streams,
# PostgreSQL and Firebase Cloud Messaging. This script prepares everything
# needed to run the pipeline (enricher → engine → delivery + engagement)
# locally using uv:
#
#   1. Verifies uv is installed
#   2. Installs Python 3.13 and creates an isolated virtual environment (.venv)
#   3. Installs Python dependencies from pyproject.toml / uv.lock
#   4. Scaffolds a .env file from sensible defaults (if missing)
#   5. Reminds you to provide Firebase credentials (service-account.json)
#   6. Optionally starts Redis + PostgreSQL via Docker for local dev
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh                 # full setup
#   ./setup.sh --with-infra    # also start local Redis + PostgreSQL in Docker
#
set -euo pipefail

# ----------------------------------------------------------------------------
# Pretty output helpers
# ----------------------------------------------------------------------------
RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; BLUE=$'\033[0;34m'; NC=$'\033[0m'
info()  { printf "%s==>%s %s\n" "$BLUE" "$NC" "$*"; }
ok()    { printf "%s ✓%s %s\n" "$GREEN" "$NC" "$*"; }
warn()  { printf "%s !%s %s\n" "$YELLOW" "$NC" "$*"; }
err()   { printf "%s ✗%s %s\n" "$RED" "$NC" "$*" >&2; }

# ----------------------------------------------------------------------------
# Resolve project root (directory this script lives in)
# ----------------------------------------------------------------------------
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# ----------------------------------------------------------------------------
# Parse flags
# ----------------------------------------------------------------------------
WITH_INFRA=0
for arg in "$@"; do
  case "$arg" in
    --with-infra) WITH_INFRA=1 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//' | sed -n '2,30p'
      exit 0
      ;;
    *) warn "Unknown argument: $arg (ignored)" ;;
  esac
done

# ----------------------------------------------------------------------------
# 1. Verify uv
# ----------------------------------------------------------------------------
info "Checking for uv ..."
if ! command -v uv >/dev/null 2>&1; then
  err "uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
ok "Found $(uv --version)"

# ----------------------------------------------------------------------------
# 2. Install Python 3.13 and sync dependencies
# ----------------------------------------------------------------------------
info "Installing Python 3.13 and syncing dependencies ..."
uv sync
ok "Dependencies installed into .venv"

# ----------------------------------------------------------------------------
# 3. Environment file (.env)
# ----------------------------------------------------------------------------
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    info "Creating .env from .env.example ..."
    cp .env.example .env
  else
    info "Creating .env with development defaults ..."
    cat > .env <<'ENV'
SERVICE_NAME=notifty
ENV=dev
DEBUG=1
DEEPLINK_SCHEME=notifty
REDIS_URL=redis://localhost:6379/0
REDIS_RAW_STREAM=notif_events_raw
REDIS_ENRICHED_STREAM=notif_events_enriched
REDIS_DELIVERY_STREAM=notif_delivery_tasks
REDIS_DLQ_STREAM=notif_events_dlq
REDIS_STREAM_MAX_LENGTH=100000
REDIS_STREAM_TTL_SECONDS=172800
DB_HOST=localhost
DB_PORT=5432
DB_NAME=notification_db
DB_USER=postgres
DB_PASSWORD=postgres
FIREBASE_SERVICE_ACCOUNT_JSON=
ENV
  fi
  ok ".env created — review and adjust credentials as needed"
else
  ok ".env already exists — leaving it untouched"
fi

# ----------------------------------------------------------------------------
# 4. Firebase service account
# ----------------------------------------------------------------------------
if [ -f service-account.json ]; then
  if grep -qE '^FIREBASE_SERVICE_ACCOUNT_JSON=\s*$' .env 2>/dev/null; then
    info "Embedding service-account.json into .env ..."
    SA_JSON="$(uv run python -c 'import json,sys; print(json.dumps(json.load(open("service-account.json"))))')"
    grep -v '^FIREBASE_SERVICE_ACCOUNT_JSON=' .env > .env.tmp && mv .env.tmp .env
    printf "FIREBASE_SERVICE_ACCOUNT_JSON='%s'\n" "$SA_JSON" >> .env
    ok "Firebase credentials embedded into .env"
  else
    ok "service-account.json present (FIREBASE_SERVICE_ACCOUNT_JSON already set)"
  fi
else
  warn "No service-account.json found."
  warn "Download your Firebase service account key and either:"
  warn "  • place it at ./service-account.json and re-run this script, or"
  warn "  • paste its JSON into FIREBASE_SERVICE_ACCOUNT_JSON in .env"
  warn "Delivery worker (FCM) will not start without valid credentials."
fi

# ----------------------------------------------------------------------------
# 5. Optional local infrastructure (Redis + PostgreSQL via Docker)
# ----------------------------------------------------------------------------
if [ "$WITH_INFRA" -eq 1 ]; then
  if command -v docker >/dev/null 2>&1; then
    info "Starting local Redis (notif-redis) ..."
    if [ -z "$(docker ps -q -f name=^/notif-redis$)" ]; then
      if [ -n "$(docker ps -aq -f name=^/notif-redis$)" ]; then docker rm -f notif-redis >/dev/null; fi
      docker run -d --name notif-redis -p 6379:6379 redis:7-alpine >/dev/null
      ok "Redis running on localhost:6379"
    else
      ok "Redis already running"
    fi

    info "Starting local PostgreSQL (notif-postgres) ..."
    if [ -z "$(docker ps -q -f name=^/notif-postgres$)" ]; then
      if [ -n "$(docker ps -aq -f name=^/notif-postgres$)" ]; then docker rm -f notif-postgres >/dev/null; fi
      docker run -d --name notif-postgres -p 5432:5432 \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=postgres \
        -e POSTGRES_DB=notification_db \
        postgres:16-alpine >/dev/null
      ok "PostgreSQL running on localhost:5432 (db: notification_db)"
    else
      ok "PostgreSQL already running"
    fi
  else
    err "Docker not found — cannot start local infra. Install Docker or run Redis/PostgreSQL manually."
  fi
else
  warn "Skipping local infra. Ensure Redis and PostgreSQL are reachable, or re-run with --with-infra"
fi

# ----------------------------------------------------------------------------
# Done — next steps
# ----------------------------------------------------------------------------
echo
ok "Setup complete!"
echo
info "Next steps:"
cat <<'STEPS'

   # Run the pipeline stages (separate terminals):
   uv run python -m app.enrichers.worker
   uv run python -m app.engine.worker
   uv run python -m app.delivery.worker
   uv run python -m app.engagement.scheduler

   # Or activate the venv and run directly:
   source .venv/bin/activate
   python -m app.enrichers.worker

   # Or run everything in one container via Supervisord:
   supervisord -n -c supervisord.conf

   # Or via Docker Compose (multi-container):
   docker-compose up

   # Inject a test event / inspect streams:
   uv run python scripts/produce_test_event.py
   uv run python scripts/consume_test_stream.py
STEPS
