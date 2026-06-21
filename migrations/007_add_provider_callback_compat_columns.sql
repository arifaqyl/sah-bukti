ALTER TABLE provider_callback_events ADD COLUMN transaction_reference TEXT;
ALTER TABLE provider_callback_events ADD COLUMN raw_payload TEXT;
ALTER TABLE provider_callback_events ADD COLUMN proof_id INTEGER;
ALTER TABLE provider_callback_events ADD COLUMN received_at TEXT;
