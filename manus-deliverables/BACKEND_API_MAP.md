BACKEND API CONTRACT (reference only — e.g., required endpoints for Manus AI)
==============================================================================
Base URL: /api/v1
Auth header: Authorization: Bearer <token>

POST /api/v1/auth/signup
  body: {email, password, display_name?, business_name?}
  returns: {access_token, token_type, user}

POST /api/v1/auth/login
  body: {email, password}
  returns: {access_token, token_type, user}

GET /api/v1/auth/me
  headers: Authorization: Bearer <token>
  returns: user object

GET /api/v1/auth/memberships
  returns: list[{id, user_id, business_id, role, created_at, business_name}]

POST /api/v1/auth/logout
  returns: {ok: true}

GET /api/v1/businesses
  returns: list businesses for current user

GET /api/v1/business/profile
  returns: business profile (name, tagline, theme_color, etc.)

GET /api/v1/customers
  returns: list customers for business

POST /api/v1/customers
  body: CustomerCreate
  returns: CustomerResponse

GET /api/v1/invoices
  returns: list invoices for business

POST /api/v1/invoices
  body: InvoiceCreate
  returns: InvoiceResponse

GET /api/v1/invoices/{invoice_id}
  returns: InvoiceResponse

PATCH /api/v1/invoices/{invoice_id}
  body: InvoiceUpdate
  returns: InvoiceResponse

GET /api/v1/invoices/export?format=csv|json
  returns: exported invoices

GET /api/v1/inventory
  returns: inventory list

GET /api/v1/evidence
  returns: evidence list

POST /api/v1/evidence/ingest (or similar evidence import)
  returns: parsed evidence

GET /api/v1/review
  returns: pending proofs

POST /api/v1/review/{proof_id}/approve|reject
  returns: updated proof

GET /api/v1/readiness
  returns: month-end readiness data

GET /api/v1/export
  returns: accountant export

GET /api/v1/health
  returns: health status

FRONTEND ROUTES (hash-based SPA)
/
/auth
/dashboard
/profile
/customers
/invoices
/invoices/new
/invoices/:id
/evidence
/review
/inventory
/readiness
/export
/help

DESIGN SYSTEM TOKENS (copy exactly from REFERENCE files)
- fonts: 'DM Sans' (sans) + 'Fraunces' (serif)
- clay: #C75B39
- bg: #F5F1EB
- surface: #FDFBF7
- ink: #1A1A1A
- muted: #8A7F72
- border: rgba(0,0,0,0.08)
- radius: 16-22px cards
- shadow: 0 1px 2px rgba(0,0,0,0.04) + 0 8px 24px rgba(0,0,0,0.06)
