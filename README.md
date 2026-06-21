# Sah.Bukti

Proof before payment. Clean books after.

Sah.Bukti gives Malaysian micro-sellers a personal WhatsApp ops lane: capture order messages, mark payment intent, review it, approve it, then safely update the ledger and month-end outputs.

Status: `66/66` backend tests green. `3/3` demo scripts green.

## Product Truth

Sah.Bukti is a backend-first collections ops system for Malaysian micro-SMEs.

It is not a autonomous accountant, a full accounting suite, or an ERP. WhatsApp is the daily command center; the product is the trust boundary:

```text
WhatsApp / CSV / order text / payment messages
        ->
evidence ingestion
        ->
review queue
        ->
owner approval
        ->
safe ledger update
        ->
reminders
        ->
accountant export
        ->
month-end readiness
```

## Safety Model

1. AI, imports, webhooks, and forwarded messages can suggest.
2. Evidence never confirms payment truth by itself.
3. Payment-like input becomes `payment_proofs` in `needs_review`.
4. Order-like input becomes a pending invoice or draftable evidence.
5. Approval is the only path that records payment and changes invoice payment status.
6. SQLite is the local source of truth.

## What Works

- Tenant-scoped auth and business context
- Customer and invoice operations
- Personal WhatsApp-style order and payment intake through `/api/v1/evidence/whatsapp`
- Secret-protected WhatsApp webhook through `/api/v1/webhook/whatsapp`
- Payment proof upload and review queue
- Owner approval and rejection audit trail
- Payment links with mock and manual QR provider shape
- Payment provider callbacks are not mounted in the demo path; payment proof review remains the source of truth
- Reminder policies and reminder queue
- Accountant export
- Month-end readiness
- MFRS 9 compliant provision for doubtful debts
- CSV / WhatsApp export evidence import
- Lightweight React frontend served by FastAPI

## API Surface

- `GET /health`
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `GET /api/v1/businesses`
- `GET /api/v1/business/profile`
- `PATCH /api/v1/business/profile`
- `POST /api/v1/customers`
- `GET /api/v1/customers`
- `POST /api/v1/invoices`
- `GET /api/v1/invoices`
- `GET /api/v1/invoices/{invoice_id}`
- `PATCH /api/v1/invoices/{invoice_id}`
- `POST /api/v1/invoices/{invoice_id}/payment` returns `410`; use payment proof review instead.
- `POST /api/v1/payments/invoices/{invoice_id}/payment-link`
- `POST /api/v1/payment-proofs/upload`
- `GET /api/v1/payment-proofs`
- `GET /api/v1/payment-proofs/{proof_id}`
- `POST /api/v1/payment-proofs/{proof_id}/approve`
- `POST /api/v1/payment-proofs/{proof_id}/reject`
- `GET /api/v1/review/payment-proofs`
- `GET /api/v1/review/reminders`
- `GET /api/v1/audit/payment-proofs/{proof_id}`
- `GET /api/v1/audit/reminders/{reminder_id}`
- `GET /api/v1/audit/callbacks`
- `POST /api/v1/daily-close`
- `GET /api/v1/daily-ops`
- `GET /api/v1/daily-ops/{date}`
- `POST /api/v1/parse-order`
- `POST /api/v1/evidence/whatsapp`
- `POST /api/v1/evidence/import`
- `POST /api/v1/webhook/whatsapp`
- `POST /api/v1/whatsapp/webhook`
- `POST /api/v1/whatsapp/agent/command`
- `POST /api/v1/inventory/ingredients`
- `GET /api/v1/inventory/ingredients`
- `PATCH /api/v1/inventory/ingredients/{ingredient_id}`
- `GET /api/v1/inventory/reorder`
- `GET /api/v1/inventory/suppliers`
- `GET /api/v1/invoices/export`
- `GET /api/v1/daily-ops/export`
- `GET /api/v1/inventory/export`
- `GET /api/v1/exports/accountant`
- `GET /api/v1/month-end/readiness`

## Demo Scripts

Run sequentially from `D:\kedai-ops`:

```powershell
.\.venv\Scripts\python.exe scripts\demo_hackathon_flow.py
.\.venv\Scripts\python.exe scripts\demo_whatsapp_evidence.py
.\.venv\Scripts\python.exe scripts\demo_evidence_import.py
```

The strongest demo spine:

1. Customer sends `nasi lemak dua`.
2. Sah.Bukti creates a pending invoice using the demo menu price.
3. Customer sends `dah bayar`.
4. Sah.Bukti creates a reviewable proof linked to the latest open invoice.
5. Owner approves proof.
6. Invoice becomes paid and exports update from approved truth.

## Frontend

The served frontend is the built React app in `frontend/`.

```powershell
cd D:\kedai-ops\manus-output
pnpm install
pnpm build
Copy-Item -Recurse -Force .\dist\public\* ..\frontend\
```

FastAPI serves:

- `/`
- `/frontend/`
- `/pay.html`
- `/assets/*`

Old static HTML surfaces are not part of the product surface.

## WhatsApp Agent

Sah.Bukti uses WAHA as the production WhatsApp HTTP adapter. The seller can send order text or payment messages into WhatsApp; the backend structures them into pending invoices or reviewable proofs, then waits for owner approval before ledger mutation.

Owner commands:

- `approve [id]`
- `reject [id]`
- `status`
- `today`
- `customer [phone]`
- `stock [item]`
- `menu`
- `receipt [id]`
- `remind [phone]`
- `help`

WAHA webhook target:

```text
http://<public-backend-host>/api/v1/whatsapp/webhook
Header: x-sahbukti-webhook-secret: <SAHBUKTI_WEBHOOK_SECRET>
```

## Local WhatsApp Bridge

```powershell
cd D:\kedai-ops
npm install
$env:SAHBUKTI_WHATSAPP_WEBHOOK_URL='http://127.0.0.1:8000/api/v1/webhook/whatsapp'
$env:SAHBUKTI_WEBHOOK_SECRET='change-me'
node .\scripts\whatsapp_bridge.js
```

Use this only as a local fallback adapter. Production uses WAHA. Webhooks fail closed when `SAHBUKTI_WEBHOOK_SECRET` is missing.

Real WhatsApp connection options:

- Personal intake demo: run `scripts\whatsapp_bridge.js`, scan the QR, then forward seller messages to the connected WhatsApp session.
- Backend webhook: POST signed messages to `/api/v1/whatsapp/webhook` with `x-sahbukti-webhook-secret`.
- Authenticated evidence lane: POST to `/api/v1/evidence/whatsapp` with a valid bearer token and `business_id`.

## Environment

Important:

- `SAHBUKTI_WEBHOOK_SECRET`
- `SAHBUKTI_WHATSAPP_PROVIDER=waha`
- `SAHBUKTI_WHATSAPP_BRIDGE_URL=http://127.0.0.1:3000`
- `SAHBUKTI_WHATSAPP_SESSION_NAME`
- `SAHBUKTI_WHATSAPP_WEBHOOK_URL`
- `SAHBUKTI_API_URL`
- `SAHBUKTI_ACCESS_TOKEN`
- `SAHBUKTI_WHATSAPP_EVIDENCE_URL`
- `SAHBUKTI_MOCK_TRANSCRIPT`

Not mounted in the demo path:

- `BILLPLZ_API_KEY`
- `BILLPLZ_COLLECTION_ID`
- `BILLPLZ_X_SIGNATURE_KEY`

Billplz provider code remains as an optional future adapter, but the webhook route is not exposed by the demo app.

## Run Backend

```powershell
cd D:\kedai-ops
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/frontend/`.

## Testing

Run sequentially:

```powershell
cd D:\kedai-ops
.\.venv\Scripts\python.exe -m pytest -q tests
```

Do not run pytest in parallel here. SQLite can produce false FK or locking failures under parallel test execution.

## Positioning

One sentence:

Sah.Bukti lets Malaysian sellers forward messy WhatsApp evidence into one control plane, review it, approve it, and safely hand month-end to an accountant.

Thirty-second pitch:

Malaysian micro-sellers already close sales in WhatsApp, but their order details, payment messages, reminders, and month-end handoff stay scattered across chats, CSVs, and memory. Sah.Bukti gives them a personal ops lane: capture the message, structure it, review it, approve it, and only then update the ledger. That keeps fast WhatsApp selling while making the books accountant-ready.
