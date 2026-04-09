-- PostgreSQL schema (spec: persistence + corrections)
CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    txn_id TEXT NOT NULL,
    user_id TEXT DEFAULT 'default',
    payload JSONB NOT NULL,
    category TEXT,
    confidence DOUBLE PRECISION,
    source TEXT,
    source_file TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_transactions_txn_id ON transactions (txn_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions (created_at DESC);

CREATE TABLE IF NOT EXISTS corrections (
    id BIGSERIAL PRIMARY KEY,
    txn_id TEXT NOT NULL,
    correct_category TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_corrections_created ON corrections (created_at DESC);

CREATE TABLE IF NOT EXISTS parse_events (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT,
    format TEXT,
    success BOOLEAN,
    row_count INT,
    latency_ms DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS anomaly_actions (
    txn_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    note TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_anomaly_actions_updated ON anomaly_actions (updated_at DESC);
