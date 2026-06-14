# notifty

A distributed, event-driven **notification platform** built on **Redis Streams** —
turning domain events into timely, personalized, multi-language push notifications
via **Firebase Cloud Messaging (FCM)**, with at-least-once delivery, idempotency,
crash recovery, and a built-in campaign engine.

**Stack:** Python 3.11 · Redis Streams · PostgreSQL · Firebase Cloud Messaging · Docker · Supervisord

![CI](https://github.com/Suhaanthsuhi/notification-platform/actions/workflows/ci.yml/badge.svg)

---

## The problem this solves

Most products start with notifications wired directly into request handlers:
the checkout endpoint calls FCM, the cron job loops over users and sends. That
works until it doesn't — a provider hiccup drops messages, a retry double-sends,
a marketing blast throttles transactional alerts, and adding one new notification
means touching five services.

notifty is the pattern that fixes that: a **standalone, horizontally scalable
pipeline** that any number of services can emit *facts* into, and which takes full
responsibility for **whether, what, when, and how** a notification is delivered —
reliably, exactly once from the user's perspective, and without coupling producers
to delivery.

It was extracted from a system running in production at ~10k events/sec and
rebuilt here as a clean, domain-agnostic reference implementation you can read,
run, and adapt.

---

## What's interesting about it (engineering highlights)

- **At-least-once delivery on Redis Streams** — consumer groups (`XREADGROUP`)
  with explicit `XACK`; nothing leaves a stream until it's processed.
- **Idempotency at every stage** — `SETNX` keys make retries and duplicate
  upstream events safe; a user never gets the same notification twice.
- **Crash recovery** — a recovery loop uses `XPENDING` + `XCLAIM` to reclaim
  messages owned by workers that died mid-process.
- **Dead-letter queue** — every stage isolates bad messages with their error,
  so one poison event can't stall the pipeline.
- **Bounded memory** — streams self-trim by age (MINID) *and* size (MAXLEN).
- **Layered rate limiting** — per-user hourly throttle + per-campaign cooldown +
  daily campaign cap, all as atomic Redis counters.
- **Pluggable everything** — events, enrichment loaders, templates, campaigns,
  and segments are all registered with decorators; adding one never requires
  touching a worker. A startup contract validator fails fast if they drift.
- **Multi-language rendering** — templates resolve copy from a translation table
  using the user's profile language (ships with `en` + `es`).
- **Async end-to-end** — all I/O (Redis, PostgreSQL, FCM) is async for high
  per-process concurrency.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the deep dive.

---

## Architecture at a glance

```
┌─────────────────────────────────────────────────────────────┐
│  PRODUCERS                                                    │
│  Upstream services            Engagement scheduler           │
│  (user / subscription /       (campaign runner,              │
│   usage / report events)       fixed cadence)               │
└──────────────┬──────────────────────────┬───────────────────┘
               ▼                          ▼
          ┌──────────────────────────────────┐
          │  notif_events_raw  (Redis Stream) │
          └───────────────┬──────────────────┘
                          │ XREADGROUP
                          ▼
          ┌──────────────────────────────────┐
          │ Stage 1 — Context Enricher        │
          │ validate · idempotency · load     │
          │ profile/preferences · publish     │
          └───────────────┬──────────────────┘
                          ▼
          ┌──────────────────────────────────┐
          │ notif_events_enriched             │
          └───────────────┬──────────────────┘
                          │ XREADGROUP
                          ▼
          ┌──────────────────────────────────┐
          │ Stage 2 — Decision Engine         │
          │ opt-in · throttle · render        │
          │ template (multi-language)         │
          └───────────────┬──────────────────┘
                          ▼
          ┌──────────────────────────────────┐
          │ notif_delivery_tasks              │
          └───────────────┬──────────────────┘
                          │ XREADGROUP
                          ▼
          ┌──────────────────────────────────┐
          │ Stage 3 — Delivery Worker         │
          │ resolve tokens · FCM send ·       │
          │ deactivate invalid tokens         │
          └───────────────┬──────────────────┘
                          ▼
                    ┌──────────────┐
                    │  FCM / APNs  │
                    └──────────────┘

          notif_events_dlq  ← failures from every stage
```

Three flows, one pipeline:

- **Transactional** — services emit `USER_REGISTERED`, `SUBSCRIPTION_EXPIRED`,
  `WEEKLY_REPORT_READY`, etc.
- **Manual** — operators trigger one-off campaigns with content supplied at
  trigger time (e.g. `SUBSCRIPTION_PAGE_ABANDONMENT`).
- **Engagement** — the scheduler segments users and emits lifecycle-marketing
  events (`ENG_FINISH_ONBOARDING`, `ENG_TRIAL_ENDING_SOON`, `ENG_WINBACK`, …).

All three converge on the same enrich → decide → deliver path, so campaigns get
identical reliability guarantees to transactional events.

---

## Quick start

### Option A — Docker Compose (everything, one command)

Brings up Redis, PostgreSQL (schema + demo seed auto-applied), and all four
workers:

```bash
cp .env.example .env          # add FIREBASE_SERVICE_ACCOUNT_JSON to actually send pushes
docker compose up --build
```

Then, from another shell, push a test event through the pipeline:

```bash
docker compose exec enricher python -m scripts.produce_test_event USER_REGISTERED user_alice
docker compose exec enricher python -m scripts.consume_test_stream delivery
```

### Option B — Local Python

```bash
./setup.sh --with-infra       # venv + deps + .env + local Redis/Postgres in Docker
source .venv/bin/activate

# apply the demo schema + seed
psql "postgresql://postgres:postgres@localhost:5432/notification_db" -f db/schema.sql
psql "postgresql://postgres:postgres@localhost:5432/notification_db" -f db/seed.sql

# run the stages (separate terminals), or all-in-one via supervisord
python -m app.enrichers.worker
python -m app.engine.worker
python -m app.delivery.worker
python -m app.engagement.scheduler
# or: supervisord -n -c supervisord.conf
```

> The enricher and engine run **without** Firebase credentials — only the
> delivery worker needs `FIREBASE_SERVICE_ACCOUNT_JSON` to actually send pushes.

---

## Event catalog (demo)

The shipped catalog is a generic SaaS example set — swap it for your product's
events. Adding a type means: add to `EventType`, register a schema, a template,
and translations (the contract validator enforces all four at startup).

| Category | Events |
|---|---|
| User lifecycle | `USER_REGISTERED` |
| Subscription | `SUBSCRIPTION_NOT_STARTED`, `SUBSCRIPTION_TRIAL_STARTED`, `SUBSCRIPTION_ACTIVE`, `SUBSCRIPTION_CANCELLED`, `SUBSCRIPTION_EXPIRED`, `SUBSCRIPTION_PAGE_ABANDONMENT` |
| Usage / quota | `ALERT_API_USAGE_LIMIT_REACHED`, `ALERT_STORAGE_LIMIT_REACHED` |
| Async jobs / reports | `WEEKLY_REPORT_READY`, `EXPORT_READY` |
| Engagement | `ENG_FINISH_ONBOARDING`, `ENG_COMPLETE_PROFILE`, `ENG_FEATURE_ADOPTION`, `ENG_INACTIVITY_NUDGE`, `ENG_WEEKLY_DIGEST`, `ENG_NEW_FEATURE_ANNOUNCEMENT`, `ENG_USERS_LIKE_YOU`, `ENG_TRY_FREE_PLAN`, `ENG_TRIAL_ENDING_SOON`, `ENG_WINBACK` |

---

## Extending it

Every capability is a registry + decorator — no worker edits required.

**A new notification type:**

```python
# 1. contracts/event_types.py
class EventType(str, Enum):
    INVOICE_PAID = "INVOICE_PAID"

# 2. contracts/events/billing.py
@register_event_model(EventType.INVOICE_PAID)
class InvoicePaidData(BaseModel):
    invoice_id: str
    amount: str

# 3. app/engine/templates/base.py
@register_template("INVOICE_PAID", "push")
def invoice_paid_v1(enriched_event: dict) -> dict:
    ...

# 4. add "INVOICE_PAID" copy to app/engine/templates/translations.py
```

**A new enrichment loader:**

```python
@register_loader
class DeviceContextLoader(BaseContextLoader):
    async def load(self, event):
        return {"device": await fetch_device_info(event.target.user_id)}
```

**A new campaign + segment:** implement `BaseCampaign` / `BaseSegment` and apply
`@register_campaign` / `@register_segment`.

---

## Reliability & rate limiting

| Concern | Mechanism |
|---|---|
| At-least-once | Consumer groups + `XACK` (ack only after success) |
| Idempotency | `SETNX notif:processed:<id>` / `engine:processed:<id>` (24h TTL) |
| Crash recovery | `XPENDING` → idle > 45s → `XCLAIM` → reprocess |
| Dead letters | `notif_events_dlq` with original payload + error |
| Stream bounds | MINID (age, 2 days) + MAXLEN (100k) trimming on every write |
| User throttle | `INCR throttle:user:<id>` — 3 / hour |
| Campaign cooldown | `notif:cooldown:<id>:<event>` — per-campaign TTL |
| Daily campaign cap | `INCR campaign:daily:<id>` — 3 / day |

---

## Horizontal scaling

Each stage is stateless and load-balanced automatically by Redis consumer groups:

```bash
docker compose up --scale enricher=5 --scale engine=10 --scale delivery=10
```

In single-container deployments, **Supervisord** runs all four workers with
`autorestart=true`.

---

## Configuration

All configuration is environment-driven (see [`.env.example`](.env.example)):

| Variable | Default | Description |
|---|---|---|
| `SERVICE_NAME` | `notifty` | Service name |
| `ENV` | `dev` | Environment label |
| `DEBUG` | `1` | Verbose logging / SQL echo |
| `DEEPLINK_SCHEME` | `notifty` | URL scheme used in notification deep links |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `REDIS_RAW_STREAM` | `notif_events_raw` | Raw events stream |
| `REDIS_ENRICHED_STREAM` | `notif_events_enriched` | Enriched events stream |
| `REDIS_DELIVERY_STREAM` | `notif_delivery_tasks` | Delivery tasks stream |
| `REDIS_DLQ_STREAM` | `notif_events_dlq` | Dead-letter queue stream |
| `REDIS_STREAM_MAX_LENGTH` | `100000` | Max entries per stream |
| `REDIS_STREAM_TTL_SECONDS` | `172800` | Stream entry age trim (2 days) |
| `DB_HOST` / `DB_PORT` | `localhost` / `5432` | PostgreSQL host / port |
| `DB_NAME` | `notification_db` | Database name |
| `DB_USER` / `DB_PASSWORD` | `postgres` / `postgres` | DB credentials |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | — | Service-account JSON (string); delivery worker only |

---

## Project layout

```
notifty/
├── contracts/              # Shared event contracts (the cross-service API)
│   ├── event_types.py      # EventType enum — the catalog
│   ├── event_base.py       # RawEvent + EventTarget
│   ├── event_registry.py   # EVENT_SCHEMA_REGISTRY + @register_event_model
│   ├── validator.py        # fail-fast contract validation at startup
│   └── events/             # per-event Pydantic data schemas
├── core/                   # Infrastructure (config, async Redis client, utils)
├── app/
│   ├── enrichers/          # Stage 1 — validate, idempotency, context loaders
│   ├── engine/             # Stage 2 — decision, throttling, templates, i18n
│   ├── delivery/           # Stage 3 — FCM transport
│   ├── engagement/         # campaign engine (scheduler, campaigns, segments)
│   └── db/                 # async SQLAlchemy repositories
├── db/                     # schema.sql + seed.sql (generic demo data model)
├── scripts/                # produce / inspect helpers
├── Dockerfile · docker-compose.yml · supervisord.conf
└── setup.sh · .env.example · requirements.txt
```

---

## Deployment

The repo ships a multi-stage `Dockerfile` (Python 3.11 slim + Supervisord) and a
`docker-compose.yml` for multi-container deployment. CI (GitHub Actions) builds
the image and runs the contract validation on every push/PR. Bring your own
orchestrator (ECS, Kubernetes, Nomad, …) — the workers are plain stateless
processes configured entirely through environment variables.

---

## License

[MIT](LICENSE) — contributions welcome, see [CONTRIBUTING.md](CONTRIBUTING.md).
