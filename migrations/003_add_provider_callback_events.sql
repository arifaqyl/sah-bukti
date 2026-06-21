CREATE TABLE IF NOT EXISTS provider_callback_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    event_key TEXT NOT NULL,
    invoice_number TEXT,
    transaction_id TEXT,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    signature_valid INTEGER NOT NULL DEFAULT 0,
    processing_status TEXT NOT NULL,
    processed_invoice_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TEXT,
    FOREIGN KEY(processed_invoice_id) REFERENCES invoices(id),
    UNIQUE(provider, event_key)
);

CREATE INDEX IF NOT EXISTS idx_provider_callback_events_provider_created
ON provider_callback_events(provider, created_at);

CREATE INDEX IF NOT EXISTS idx_provider_callback_events_invoice
ON provider_callback_events(invoice_number);
