#!/usr/bin/env bash
#
# setup.sh — Local development setup for notifty (notification platform)
#
# A distributed, event-driven notification system built on Redis Streams,
# PostgreSQL and Firebase Cloud Messaging. This script prepares everything
# needed to run the pipeline (enricher → engine → delivery + engagement)
# locally:
#
#   1. Verifies the required tooling (Python 3.11, pip)
#   2. Creates an isolated virtual environment (.venv)
#   3. Installs Python dependencies from requirements.txt
#   4. Scaffolds a .env file from sensible defaults (if missing)
#   5. Reminds you to provide Firebase credentials (service-account.json)
#   6. Optionally starts Redis + PostgreSQL via Docker for local dev
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh                 # full setup
#   ./setup.sh --with-infra    # also start local Redis + PostgreSQL in Docker
#   ./setup.sh --no-venv       # install into the current Python environment
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
USE_VENV=1
for arg in "$@"; do
  case "$arg" in
    --with-infra) WITH_INFRA=1 ;;
    --no-venv)    USE_VENV=0 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//' | sed -n '2,30p'
      exit 0
      ;;
    *) warn "Unknown argument: $arg (ignored)" ;;
  esac
done

# ----------------------------------------------------------------------------
# 1. Locate a suitable Python interpreter (3.11.x preferred)
# ----------------------------------------------------------------------------
REQUIRED_PY="$(cat .python-version 2>/dev/null | tr -d '[:space:]' || echo '3.11.8')"
REQUIRED_MAJOR_MINOR="${REQUIRED_PY%.*}"   # e.g. 3.11

find_python() {
  for candidate in "python${REQUIRED_MAJOR_MINOR}" python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; exit(0 if sys.version_info[:2]==(3,11) else 1)' 2>/dev/null; then
        echo "$candidate"; return 0
      fi
    fi
  done
  # Fall back to any python3 if no exact 3.11 found
  command -v python3 >/dev/null 2>&1 && { echo python3; return 0; }
  return 1
}

info "Checking for Python ${REQUIRED_MAJOR_MINOR} ..."
if ! PYTHON="$(find_python)"; then
  err "No Python interpreter found. Please install Python ${REQUIRED_PY}."
  exit 1
fi
PY_VERSION="$("$PYTHON" -V 2>&1)"
if ! "$PYTHON" -c 'import sys; exit(0 if sys.version_info[:2]==(3,11) else 1)' 2>/dev/null; then
  warn "Using ${PY_VERSION} — project targets Python ${REQUIRED_PY}. Continuing anyway."
else
  ok "Found ${PY_VERSION} (${PYTHON})"
fi

# ----------------------------------------------------------------------------
# 2. Virtual environment
# ----------------------------------------------------------------------------
if [ "$USE_VENV" -eq 1 ]; then
  if [ ! -d .venv ]; then
    info "Creating virtual environment at .venv ..."
    "$PYTHON" -m venv .venv
    ok "Virtual environment created"
  else
    ok "Virtual environment already exists (.venv)"
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  PYTHON="python"
else
  warn "Skipping virtualenv (--no-venv); installing into current environment"
fi

# ----------------------------------------------------------------------------
# 3. Install dependencies
# ----------------------------------------------------------------------------
info "Upgrading pip ..."
"$PYTHON" -m pip install --upgrade pip >/dev/null
info "Installing Python dependencies from requirements.txt ..."
"$PYTHON" -m pip install -r requirements.txt
ok "Dependencies installed"

# ----------------------------------------------------------------------------
# 4. Environment file (.env)
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
# 5. Firebase service account
# ----------------------------------------------------------------------------
# The app reads the credential as a JSON *string* from FIREBASE_SERVICE_ACCOUNT_JSON.
# If a service-account.json file is present and the env var is empty, embed it.
if [ -f service-account.json ]; then
  if grep -qE '^FIREBASE_SERVICE_ACCOUNT_JSON=\s*$' .env 2>/dev/null; then
    info "Embedding service-account.json into .env ..."
    # Compact the JSON to a single line and escape for safe single-quoting
    SA_JSON="$("$PYTHON" -c 'import json,sys; print(json.dumps(json.load(open("service-account.json"))))')"
    # Remove the empty line and append the populated one
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
# 6. Optional local infrastructure (Redis + PostgreSQL via Docker)
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
if [ "$USE_VENV" -eq 1 ]; then
  echo "   source .venv/bin/activate"
fi
cat <<'STEPS'

   # Run the pipeline stages (separate terminals):
   python -m app.enrichers.worker
   python -m app.engine.worker
   python -m app.delivery.worker
   python -m app.engagement.scheduler

   # Or run everything in one container via Supervisord:
   supervisord -n -c supervisord.conf

   # Or via Docker Compose (multi-container):
   docker-compose up

   # Inject a test event / inspect streams:
   python scripts/produce_test_event.py
   python scripts/consume_test_stream.py
STEPS
