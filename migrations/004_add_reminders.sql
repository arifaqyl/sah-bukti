CREATE TABLE IF NOT EXISTS reminder_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'mock',
    min_days_overdue INTEGER NOT NULL DEFAULT 1,
    cadence_days INTEGER NOT NULL DEFAULT 3,
    enabled INTEGER NOT NULL DEFAULT 1,
    template_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(business_id) REFERENCES businesses(id)
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    invoice_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    policy_id INTEGER NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    days_overdue INTEGER NOT NULL DEFAULT 0,
    outstanding_amount REAL NOT NULL DEFAULT 0,
    message_text TEXT NOT NULL,
    dedupe_key TEXT NOT NULL,
    generated_for_date TEXT NOT NULL,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    last_error TEXT,
    FOREIGN KEY(business_id) REFERENCES businesses(id),
    FOREIGN KEY(invoice_id) REFERENCES invoices(id),
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(policy_id) REFERENCES reminder_policies(id),
    UNIQUE(business_id, dedupe_key)
);

CREATE TABLE IF NOT EXISTS reminder_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reminder_id INTEGER NOT NULL,
    actor_user_id INTEGER,
    event_type TEXT NOT NULL,
    event_payload TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(reminder_id) REFERENCES reminders(id),
    FOREIGN KEY(actor_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_reminder_policies_business
ON reminder_policies(business_id, enabled);

CREATE INDEX IF NOT EXISTS idx_reminders_business_generated
ON reminders(business_id, generated_for_date, status);

CREATE INDEX IF NOT EXISTS idx_reminders_invoice
ON reminders(invoice_id, generated_at);

CREATE INDEX IF NOT EXISTS idx_reminder_events_reminder
ON reminder_events(reminder_id, created_at);
