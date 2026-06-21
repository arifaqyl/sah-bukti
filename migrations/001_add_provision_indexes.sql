CREATE INDEX IF NOT EXISTS idx_invoices_business_status
ON invoices(business_id, payment_status);

CREATE INDEX IF NOT EXISTS idx_invoices_due_date
ON invoices(due_date);

CREATE INDEX IF NOT EXISTS idx_provision_business_month
ON provision_snapshots(business_id, month);
