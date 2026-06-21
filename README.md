# Sah.Bukti

Proof before payment. Clean books after.

Sah.Bukti is a WhatsApp-first collections control plane for Malaysian micro-sellers. It turns messy order and payment messages into structured evidence, routes them through a review queue, and updates ledger truth only after owner approval.

Live product: `https://arifaqyl.me/frontend/`

## Product

Small sellers already live in WhatsApp. Orders, payment intent, screenshots, and follow-up all happen there first. Sah.Bukti does not try to replace that behavior. It gives the seller a control plane behind it:

```text
WhatsApp message / CSV / imported evidence
        ->
evidence capture
        ->
review queue
        ->
owner approval
        ->
ledger update
        ->
accountant export
        ->
month-end readiness
```

## Core Principles

- WhatsApp is the workflow, not the source of truth.
- Evidence can suggest, but it does not confirm payment truth by itself.
- Approval is the only path that mutates ledger state.
- Export and month-end surfaces reflect approved truth only.
- SQLite remains the local source of truth for the demo and application state.

## What Sah.Bukti Is Not

- Not a generic chatbot
- Not a full accounting suite
- Not an ERP
- Not an autonomous accounting agent
- Not an auto-payment confirmation tool

## Current Capabilities

- FastAPI backend with tenant-scoped business context
- SQLite data model for invoices, customers, payment proofs, reminders, exports, and provision snapshots
- React frontend served through FastAPI
- WhatsApp-style evidence intake and webhook normalization
- Review queue for payment proofs
- Approval and rejection audit trail
- Customer and invoice management
- Accountant export
- Month-end readiness and provision reporting

## Safety Model

The main trust rule is enforced in code:

1. Order-like input can create a pending invoice or structured evidence.
2. Payment-like input can create a payment proof in `needs_review`.
3. No inbound evidence path is allowed to mark an invoice paid by itself.
4. Only approval can create the recorded payment state that mutates invoice truth.

## Public Demo

Public frontend:

- `https://arifaqyl.me/frontend/`

Main surfaces:

- `/frontend/`
- `/api/v1/review/payment-proofs`
- `/api/v1/invoices`
- `/api/v1/exports/accountant`
- `/api/v1/month-end/readiness`

Public demo safety rule:

- the public site must not expose live WhatsApp linking QR, private owner numbers, or secret-bearing connector controls

## Local Development

Backend:

```powershell
cd D:\kedai-ops
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

Frontend:

The built frontend is served from `frontend/` by FastAPI.

Open:

```text
http://127.0.0.1:8000/frontend/
```

## Tests

Run sequentially:

```powershell
cd D:\kedai-ops
.\.venv\Scripts\python.exe -m pytest -q tests
```

Current verified status in this repository:

- backend tests green
- demo scripts green

## Documentation

- [Build log: Day 1 to Day 4](docs/day1-day4-build-log.md)
- [Challenges and decisions](docs/challenges-and-decisions.md)
- [Project build summary](docs/project-build-summary.md)
- [Demo transcript](docs/demo-transcript.txt)

## Architecture Notes

The strongest product wedge is not invoice generation in isolation. It is controlled collections ops:

- capture incoming order and payment evidence
- preserve owner review as the trust boundary
- keep invoice state tied to approved proof
- make month-end export cleaner than the original chat workflow

## License

MIT
