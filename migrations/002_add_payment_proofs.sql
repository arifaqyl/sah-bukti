CREATE TABLE IF NOT EXISTS payment_proofs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    invoice_id INTEGER,
    uploaded_by_user_id INTEGER,
    approved_payment_id INTEGER,
    source_channel TEXT NOT NULL DEFAULT 'dashboard',
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    ocr_status TEXT NOT NULL DEFAULT 'pending',
    ocr_error TEXT,
    ocr_payload TEXT,
    extracted_amount REAL,
    extracted_reference TEXT,
    extracted_paid_at TEXT,
    confidence_score REAL,
    review_state TEXT NOT NULL DEFAULT 'needs_review',
    decision_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TEXT,
    FOREIGN KEY(business_id) REFERENCES businesses(id),
    FOREIGN KEY(invoice_id) REFERENCES invoices(id),
    FOREIGN KEY(uploaded_by_user_id) REFERENCES users(id),
    FOREIGN KEY(approved_payment_id) REFERENCES payments(id),
    UNIQUE(business_id, file_hash)
);

CREATE TABLE IF NOT EXISTS payment_proof_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_proof_id INTEGER NOT NULL,
    actor_user_id INTEGER,
    event_type TEXT NOT NULL,
    event_payload TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(payment_proof_id) REFERENCES payment_proofs(id),
    FOREIGN KEY(actor_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_payment_proofs_business_created
ON payment_proofs(business_id, created_at);

CREATE INDEX IF NOT EXISTS idx_payment_proofs_invoice
ON payment_proofs(invoice_id);

CREATE INDEX IF NOT EXISTS idx_payment_proofs_reference
ON payment_proofs(business_id, extracted_reference);

CREATE INDEX IF NOT EXISTS idx_payment_proof_events_proof
ON payment_proof_events(payment_proof_id, created_at);
