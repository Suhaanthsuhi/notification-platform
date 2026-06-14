-- db/schema.sql
-- Demo PostgreSQL schema for the notifty notification platform.
--
-- This is the minimal data model the enricher (profile lookup), delivery
-- worker (device tokens), and engagement segments query against. It is a
-- generic SaaS shape — adapt the tables/columns to your own product.
--
-- Apply with:  psql "$DATABASE_URL" -f db/schema.sql

-- ---------------------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                    TEXT PRIMARY KEY,
    first_name            TEXT,
    last_name             TEXT,
    email                 TEXT,
    language              TEXT        DEFAULT 'en',
    onboarding_completed  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Device tokens (one row per registered device per user)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS device_tokens (
    user_id              TEXT NOT NULL REFERENCES users(id),
    device_id            TEXT NOT NULL,
    token                TEXT NOT NULL,
    platform             TEXT,                 -- 'android' | 'ios' | 'web'
    active               BOOLEAN NOT NULL DEFAULT TRUE,
    last_failure_reason  TEXT,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_device_tokens_active
    ON device_tokens (user_id) WHERE active = TRUE;

-- ---------------------------------------------------------------------------
-- Subscriptions
--   status in: ACTIVE | TRIAL | FREE | ACTIVE_CANCELLED | PAUSED
--              | CANCELLED | EXPIRED
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscriptions (
    id                        TEXT PRIMARY KEY,
    user_id                   TEXT NOT NULL REFERENCES users(id),
    plan_name                 TEXT,
    status                    TEXT NOT NULL,
    trial_started_at          TIMESTAMPTZ,
    trial_ends_at             TIMESTAMPTZ,
    started_at                TIMESTAMPTZ,
    billing_cycles_completed  INTEGER NOT NULL DEFAULT 0,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user   ON subscriptions (user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions (status);

-- ---------------------------------------------------------------------------
-- Usage counters (current billing period usage per subscription)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usage_counters (
    subscription_id  TEXT PRIMARY KEY REFERENCES subscriptions(id),
    api_calls_used   INTEGER NOT NULL DEFAULT 0,
    storage_used     INTEGER NOT NULL DEFAULT 0,   -- percent, 0-100
    period_end       TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- Plan limits per subscription
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscription_limits (
    subscription_id  TEXT PRIMARY KEY REFERENCES subscriptions(id),
    api_calls_limit  INTEGER NOT NULL DEFAULT 0,
    storage_limit    INTEGER NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------------------------
-- Free-trial usage tracking (has a user ever used their free trial?)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_trials (
    user_id    TEXT PRIMARY KEY REFERENCES users(id),
    used_free  BOOLEAN NOT NULL DEFAULT FALSE
);
