-- REZAR target PostgreSQL schema. Do not run as a migration of the live SQLite DB.
-- Production cutover requires an explicit data migration and verified rollback.
CREATE TABLE IF NOT EXISTS users (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  telegram_id BIGINT NOT NULL UNIQUE,
  username TEXT,
  first_name TEXT,
  language_code TEXT,
  first_start TIMESTAMPTZ,
  last_activity TIMESTAMPTZ,
  first_source TEXT,
  last_source TEXT,
  start_code VARCHAR(64),
  phone TEXT,
  phone_received_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS users_phone_idx ON users(phone);
CREATE INDEX IF NOT EXISTS users_first_start_idx ON users(first_start);

CREATE TABLE IF NOT EXISTS campaigns (
  code VARCHAR(64) PRIMARY KEY,
  utm_source TEXT NOT NULL,
  utm_medium TEXT NOT NULL,
  utm_campaign TEXT,
  utm_content TEXT,
  utm_term TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
  event_name TEXT NOT NULL,
  start_code VARCHAR(64),
  event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS events_date_idx ON events(created_at);
CREATE INDEX IF NOT EXISTS events_user_idx ON events(telegram_id);

CREATE TABLE IF NOT EXISTS leads (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  lead_key TEXT NOT NULL UNIQUE,
  telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
  origin TEXT NOT NULL,
  car TEXT,
  production_year TEXT,
  budget TEXT,
  contact_method TEXT,
  crm_lead_id TEXT,
  crm_status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS leads_status_idx ON leads(crm_status);

CREATE TABLE IF NOT EXISTS outbox (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  channel TEXT NOT NULL CHECK (channel IN ('keycrm','graspil')),
  entity_key TEXT NOT NULL,
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INT NOT NULL DEFAULT 0,
  next_attempt TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at TIMESTAMPTZ,
  external_id TEXT,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(channel,entity_key)
);
CREATE INDEX IF NOT EXISTS outbox_pending_idx ON outbox(next_attempt) WHERE status='pending';

CREATE TABLE IF NOT EXISTS admins (
  telegram_id BIGINT PRIMARY KEY,
  role TEXT NOT NULL CHECK(role IN ('owner','admin','marketer')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS content_overrides (
  screen_key TEXT PRIMARY KEY,
  body TEXT,
  media_file_id TEXT,
  buttons JSONB NOT NULL DEFAULT '[]'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS broadcasts (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  body TEXT NOT NULL,
  media_file_id TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_by BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS broadcast_delivery (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  broadcast_id BIGINT NOT NULL REFERENCES broadcasts(id),
  telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
  status TEXT NOT NULL DEFAULT 'pending',
  error TEXT,
  UNIQUE(broadcast_id,telegram_id)
);
CREATE TABLE IF NOT EXISTS integration_errors (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  entity_key TEXT NOT NULL,
  integration TEXT NOT NULL,
  error TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);
