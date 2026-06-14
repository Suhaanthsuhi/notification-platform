-- db/seed.sql
-- Optional demo data so the pipeline and engagement segments return rows.
-- Device tokens here are placeholders — replace with real FCM tokens to
-- actually deliver pushes.
--
-- Apply with:  psql "$DATABASE_URL" -f db/seed.sql

INSERT INTO users (id, first_name, last_name, email, language, onboarding_completed) VALUES
    ('user_alice', 'Alice', 'Nguyen',  'alice@example.com', 'en', TRUE),
    ('user_bob',   'Bob',   'Garcia',  'bob@example.com',   'es', FALSE),
    ('user_carol', 'Carol', 'Smith',   'carol@example.com', 'en', FALSE)
ON CONFLICT (id) DO NOTHING;

INSERT INTO device_tokens (user_id, device_id, token, platform, active) VALUES
    ('user_alice', 'device_a1', 'REPLACE_WITH_REAL_FCM_TOKEN_1', 'android', TRUE),
    ('user_bob',   'device_b1', 'REPLACE_WITH_REAL_FCM_TOKEN_2', 'ios',     TRUE),
    ('user_carol', 'device_c1', 'REPLACE_WITH_REAL_FCM_TOKEN_3', 'web',     TRUE)
ON CONFLICT (user_id, device_id) DO NOTHING;

-- Alice: active paid subscriber, barely using the product (low-usage segment)
INSERT INTO subscriptions (id, user_id, plan_name, status, started_at, billing_cycles_completed) VALUES
    ('sub_alice', 'user_alice', 'Pro', 'ACTIVE', NOW() - INTERVAL '40 days', 1)
ON CONFLICT (id) DO NOTHING;

INSERT INTO subscription_limits (subscription_id, api_calls_limit, storage_limit) VALUES
    ('sub_alice', 10000, 100)
ON CONFLICT (subscription_id) DO NOTHING;

INSERT INTO usage_counters (subscription_id, api_calls_used, storage_used, period_end) VALUES
    ('sub_alice', 120, 5, NOW() + INTERVAL '20 days')
ON CONFLICT (subscription_id) DO NOTHING;

-- Bob: on a trial that ends in 1 day (trial_ending_soon segment)
INSERT INTO subscriptions (id, user_id, plan_name, status, trial_started_at, trial_ends_at, started_at) VALUES
    ('sub_bob', 'user_bob', 'Pro', 'TRIAL', NOW() - INTERVAL '13 days', NOW() + INTERVAL '1 day', NOW() - INTERVAL '13 days')
ON CONFLICT (id) DO NOTHING;

-- Carol: no subscription, never used free trial (winback / free-trial segments)
INSERT INTO user_trials (user_id, used_free) VALUES
    ('user_carol', FALSE)
ON CONFLICT (user_id) DO NOTHING;
