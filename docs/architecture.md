# Architecture

## Application Shape

Sah.Bukti is a backend-first application built around a narrow trust model:

- FastAPI application layer
- SQLite source of truth
- service modules for invoices, evidence, payments, exports, reminders, and provision logic
- React frontend served by FastAPI
- WhatsApp adapter layer feeding the same evidence pipeline

## Core Data Path

```text
message or imported evidence
        ->
evidence classification
        ->
pending invoice or payment proof
        ->
review decision
        ->
ledger mutation
        ->
export / readiness / provision
```

## Key Modules

- `app/services/evidence.py`: evidence normalization and routing
- `app/services/payment_proofs.py`: review queue and approval logic
- `app/services/payments.py`: recorded payments and settlement state
- `app/services/exports.py`: accountant export payloads
- `app/services/month_end.py`: readiness calculations
- `app/services/provision.py`: MFRS 9 expected credit loss provision logic
- `app/services/whatsapp.py`: transport adapter and agent behavior

## Public Deployment Rule

The public site is product-facing, not admin-facing. Live connector secrets, QR linking surfaces, and owner-only control details must stay off the public deployment.
