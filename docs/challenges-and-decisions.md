# Sah.Bukti Challenges and Decisions

## Biggest Challenges

### 1. Preventing fake confidence

The biggest product risk was drifting into a system that looked automated but did not deserve trust.

If chat messages or payment-looking input were allowed to update invoices directly, the product would become dangerous instead of useful.

### 2. Keeping the product story narrow

There was constant pressure for the product to become too many things at once:

- chatbot
- invoicing app
- accounting suite
- ERP
- generic AI assistant

That would have weakened the demo and the architecture.

### 3. Frontend and backend drift

At one point the UI story and the actual backend behavior were not cleanly aligned. Some surfaces implied more automation than the backend safely allowed.

### 4. Demo realism versus demo safety

The live WhatsApp story is strong, but public access also creates risk. Demo surfaces needed to be believable without turning the public deployment into an unsafe open intake channel.

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

## What Was Cut

- generic AI assistant positioning
- auto-confirm payment claims
- overblown Sheets / Drive story
- full accounting suite claims
- ERP drift
- public QR-based WhatsApp linking for the live demo path

## What Remains Rough

- The GitHub repository slug still says `kedai-ops`
- The live WhatsApp story is strongest in controlled demo conditions
- Some secondary surfaces exist but are not the core wedge
- The public site is good enough for judging, but the strongest story is still the guided demo

## Final Truth

The winning version of Sah.Bukti is not “AI for accounting.”

The winning version is:

forward messy WhatsApp evidence,
review it,
approve what is true,
and keep the books cleaner after.
