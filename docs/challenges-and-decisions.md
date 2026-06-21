# Sah.Bukti Challenges and Decisions

## Main Risks

### Preventing false payment confidence

The main product risk was letting chat evidence look more authoritative than it really is.

If chat messages or payment-looking input were allowed to update invoices directly, the product would become dangerous instead of useful.

### Keeping scope narrow

There was constant pressure for the product to drift into adjacent categories:

- chatbot
- invoicing app
- accounting suite
- ERP
- generic AI assistant

That would have weakened both the product story and the codebase.

### Frontend and backend drift

At one point the UI story and the actual backend behavior were not cleanly aligned. Some surfaces implied more automation than the backend safely allowed.

### Public deployment versus private operations

The WhatsApp workflow is strongest when connected to a real owner-controlled number, but public deployment introduces connector and privacy risk. The public product surface needs to stay safe even when the private operator flow is stronger.

## Key Decisions

### Approval is the only mutation path

This is the single most important system rule.

- order messages can create invoices
- payment messages can create proofs
- evidence can enter the system
- but only approval updates financial truth

### WhatsApp is the workflow, not the database

WhatsApp is where the seller already lives.
Sah.Bukti exists behind it as the control plane.

### SQLite stays the source of truth

The project avoided overbuilding infrastructure and kept the data model grounded in a simple, local system of record.

### The month-end payoff matters

Sah.Bukti is not only about intake.
The business value becomes obvious when approved records can be exported and handed off more cleanly.

## Cuts

- generic AI assistant positioning
- auto-confirm payment claims
- overblown Sheets / Drive story
- full accounting suite claims
- ERP drift
- public QR-based WhatsApp linking on the open product surface

## Remaining Constraints

- The repo path still uses `kedai-ops` locally
- The strongest operator flow is still a controlled owner workflow, not an open public connector flow
- Some secondary surfaces remain useful but are not part of the core wedge

## Product Truth

Sah.Bukti is not “AI for accounting.”

The useful version is:

forward messy WhatsApp evidence,
review it,
approve what is true,
and keep the books cleaner after.
