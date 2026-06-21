# Sah.Bukti Backend Workflow Plan

## Goal

Build the backend workflow until Sah.Bukti is a complete ops engine. Frontend can stay minimal until the backend is stable.

Core flow:

```text
WhatsApp order -> parsed order -> invoice draft -> payment link/proof -> paid invoice -> ledger -> daily close -> inventory update -> overdue follow-up -> provision report -> export
```

## Codex Rules

1. Read relevant files before editing.
2. Do not touch frontend unless explicitly asked.
3. Do not switch to Firebase now.
4. Keep DigitalOcean + SQLite as the hackathon path.
5. Keep Billplz optional. Default payment provider must stay `mock`.
6. Every business-facing route must support and enforce `business_id`.
7. No public admin routes.
8. Every new workflow needs tests.
9. Do not hallucinate payment rails.
10. Build backend-first, frontend-later.

## Current Important Files

- `app/main.py`
- `app/db/store.py`
- `app/services/invoices.py`
- `app/services/payments.py`
- `app/api/routes/payments.py`
- `app/api/routes/whatsapp.py`
- `app/services/parser.py`
- `app/services/cron.py`
- `app/services/provision.py`
- `app/services/aging.py`
- `app/services/inventory.py`
- `tests/`

## Phase 1: Auth and Tenant Foundation

### Build

- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

### Data

Add:

- `users`
- `business_memberships`

### Invariants

- One user can belong to multiple businesses.
- Every business request must resolve a valid membership.
- Staff cannot access another business.
- Accountant can view/export but not mutate unless allowed.

### Tests

- signup creates user and demo business
- login returns token/session
- unauthenticated request is rejected
- user cannot access another business
- owner can access own business

## Phase 2: Business Scoping Everywhere

### Rule

Every business-facing endpoint must require business context.

Bad:

```text
GET /api/v1/invoices
```

Good:

```text
GET /api/v1/businesses/{business_id}/invoices
```

### Scope

Apply scoping to:

- customers
- invoices
- payments
- payment links
- payment proofs
- inventory
- daily close
- provision
- reminders
- exports

### Tests

- list only own business records
- create rejects cross-business customer
- payment link rejects cross-business invoice
- export rejects cross-business query

## Phase 3: Payment Provider Abstraction

### Keep

- `mock` provider as default
- Billplz as optional adapter only

### Build provider interface

```text
create_payment_link(invoice)
handle_webhook(payload)
build_payment_page_url(invoice)
```

### Providers

- `mock`: `/pay.html?id={invoice_id}`
- `billplz`: only when env vars are set

### Invariants

- No real provider call unless env vars exist.
- Webhook must verify signature if provider supports it.
- Webhook must be idempotent.
- Payment reference must be unique per invoice.

### Tests

- mock payment link returns local URL
- duplicate webhook does not create duplicate payment
- missing invoice reference fails safely
- wrong amount marks review or partial, not paid

## Phase 4: Invoice Lifecycle

### States

```text
draft -> pending -> partial -> paid -> overdue -> cancelled -> void
```

### Build

- create invoice
- update invoice
- cancel invoice
- void invoice
- mark paid manually
- calculate amount paid/outstanding
- list by status/date/customer
- export invoices

### Invariants

- Paid invoices cannot be edited except notes/metadata.
- Cancelled invoices cannot receive payment.
- Partial payments reduce outstanding amount.
- Provision must use outstanding amount, not total.

### Tests

- partial payment updates outstanding
- full payment marks paid
- duplicate payment reference is ignored
- cancelled invoice rejects payment

## Phase 5: Payment Link and Demo Payment Page

### Backend

- create payment link
- get payment link
- mark mock payment as paid
- handle provider webhook

### Frontend later

Keep `/pay.html` only as demo utility. Do not polish it yet.

### Invariants

- Payment link belongs to one invoice.
- Payment link cannot be reused after invoice is paid.
- Mock payment must not require real payment.

### Tests

- payment link creates URL
- payment page records payment
- second payment does not duplicate amount

## Phase 6: Payment Proof Workflow

### Build

- upload receipt screenshot
- AI/OCR extract amount, reference, date, bank/e-wallet
- compare against invoice
- return confidence and decision:
  - `auto_approved`
  - `needs_review`
  - `rejected`
- manual approve/reject endpoint

### Data

Add:

- `payment_proofs`

### Invariants

- OCR is triage, not truth.
- Low confidence requires review.
- Fake/edited screenshots are possible.
- Never claim proof is guaranteed.

### Tests

- matching proof approves
- amount mismatch needs review
- missing invoice fails
- duplicate proof reference is ignored

## Phase 7: WhatsApp Order Workflow

### Flow

```text
WhatsApp message -> detect payment or order -> parse -> create/update invoice -> reply
```

### Build

- detect payment intent
- detect order intent
- reject ambiguous order
- create customer if needed
- create invoice
- deduct inventory
- send reply
- return structured response

### Invariants

- Ambiguous order should not create a false invoice.
- Payment message should update invoice, not create duplicate.
- Business ID must be part of WhatsApp payload.
- WhatsApp secret must be required in production.

### Tests

- order creates invoice
- payment updates invoice
- ambiguous message returns needs_clarification
- duplicate invoice number is not created

## Phase 8: Daily Close

### Build

- run daily close for business/date
- tally paid invoices by method
- upsert daily_ops
- list daily ops
- export daily ops

### Invariants

- Daily close is idempotent.
- Recalculating a day overwrites summary safely.
- Paid status is the source of revenue.
- Payment method is normalized to `cash`, `qr`, `transfer`, or `unknown`.

### Tests

- daily close upserts one row
- recalculating same day does not duplicate
- paid invoices are counted by method
- unpaid invoices are excluded

## Phase 9: Inventory

### Build

- ingredients CRUD
- stock adjustment
- reorder alerts
- deduct ingredients on invoice/order
- export inventory

### Invariants

- Stock cannot go below zero.
- Deduction is best-effort unless exact item exists.
- Reorder alerts are per business.
- Inventory is optional but must not break order creation.

### Tests

- create ingredient
- deduct stock
- stock stops at zero
- low stock alert appears
- cross-business ingredient is not deducted

## Phase 10: Reminders and Overdue Follow-up

### Build

- calculate overdue invoices
- create reminder draft
- send reminder through WhatsApp bridge
- record notification event
- mark reminder status

### Data

Add:

- `reminders`
- `notification_events`

### Invariants

- Reminder cannot be sent for paid invoice.
- Duplicate reminder for same invoice/day is avoided.
- Failed notification is recorded.

### Tests

- overdue invoice gets reminder draft
- paid invoice cannot be reminded
- duplicate reminder is suppressed
- failed notification is logged

## Phase 11: Provision Engine

### Current state

Provision engine exists in:

- `app/services/provision.py`
- `app/services/aging.py`

### Strengthen

- Use amount_outstanding if added.
- Ensure business scoping.
- Ensure snapshots are idempotent.
- Add export for CSV/JSON.
- Add journal entry validation.

### Invariants

- Provision is calculated per business/month.
- Fully paid invoices are excluded.
- Partial invoices use outstanding amount.
- Journal entry must balance.

### Tests

- current/partial/paid invoices bucket correctly
- snapshot is idempotent
- journal entry balances
- export contains aging + journal

## Phase 12: Exports

### Build

- invoices CSV/JSON
- daily ops CSV/JSON
- inventory CSV/JSON
- provision CSV/JSON
- MyInvois-ready export shape later

### Invariants

- Exports are scoped to business.
- Exports do not expose another business.
- CSV uses stable headers.
- JSON export is machine-readable.

### Tests

- export own business only
- CSV headers are stable
- JSON contains expected fields

## Phase 13: Background Jobs

### Build

- daily close job
- monthly provision job
- overdue reminder job
- manual trigger endpoints protected by auth/admin role

### Invariants

- Jobs loop through business IDs.
- Jobs are idempotent.
- Scheduler failures are logged.
- Manual admin endpoints are not public.

### Tests

- daily close job processes all businesses
- monthly provision skips empty month
- reminder job skips paid invoices
- admin endpoint requires admin token

## Phase 14: Deployment

### Hackathon deployment

Use:

```text
DigitalOcean droplet + FastAPI + SQLite + mock payments
```

### Requirements

- Set `SAHBUKTI_APP_BASE_URL`
- Set `SAHBUKTI_WEBHOOK_SECRET`
- Set `GEMINI_API_KEY` if AI parsing is enabled
- Keep `SAHBUKTI_PAYMENT_PROVIDER=mock`
- Run one uvicorn worker
- Do not expose public admin endpoints

### Later production deployment

Use:

```text
DigitalOcean App Platform + managed Postgres + Supabase Auth or custom auth
```

## Verification Commands

Run after each phase:

```powershell
cd D:\kedai-ops
.\.venv\Scripts\python.exe -m pytest -q
```

Run app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Smoke tests:

```powershell
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/docs
```

## Definition of Done

Backend is ready when:

- Auth exists.
- Business scoping exists.
- No public admin routes.
- Invoice lifecycle works.
- Payment link mock works.
- Payment proof triage works.
- WhatsApp order/payment flow works.
- Daily close is idempotent.
- Inventory deduction works.
- Provision engine is scoped and tested.
- Exports are scoped.
- Tests pass.
- README documents backend workflow.
