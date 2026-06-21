# Sah.Bukti Day 1 to Day 4 Build Log

## Project Name

Sah.Bukti

## Tagline

Proof before payment. Clean books after.

## Core Product

Sah.Bukti is a WhatsApp-first collections control plane for Malaysian micro-sellers.

Core loop:

WhatsApp message
-> evidence capture
-> review queue
-> owner approval
-> ledger update
-> accountant export
-> month-end readiness

## Day 1

### Focus

- Set up the backend foundation
- Establish the product direction
- Get the first working operational flow running

### What happened

- FastAPI and SQLite foundation was established as the product core
- Initial UI direction and operating model were explored
- Early dashboard and ops views were assembled
- The first end-to-end product skeleton was made visible

### Why it mattered

Day 1 was about getting out of idea mode and into a real system shape. The priority was not polish. The priority was proving there was a workable base.

## Day 2

### Focus

- Evidence ingestion
- Review gating
- Import and export surfaces

### What happened

- Evidence -> review flow was built out
- Approval-gated state change became a core rule
- Import and export paths were added
- Month-end readiness direction became part of the product story

### Why it mattered

This was the day the trust model became real. Sah.Bukti stopped looking like a generic invoicing tool and started looking like a controlled ops system.

## Day 3

### Focus

- Trust boundary hardening
- WhatsApp order and payment text flow
- Frontend and backend alignment

### What happened

- Payment-like input was kept in review instead of auto-confirming
- Order text like `nasi lemak dua` was mapped into structured invoice creation
- Payment text with invoice references could create linked payment proofs
- Review queue became the single gate before ledger truth
- Frontend story was aligned more tightly to the real backend behavior

### Why it mattered

Day 3 turned Sah.Bukti from a rough prototype into something much more defensible. The important architectural line was made explicit:

messages can suggest,
but approval decides.

## Day 4

### Focus

- Public demo readiness
- Live deployment safety
- Submission packaging

### What happened

- Public site was verified on the live domain
- Frontend and API surfaces were checked against the demo story
- Brand was unified around Sah.Bukti
- Public-facing WhatsApp link UI was locked down
- Demo-safe invoice and proof flows were verified against the live system
- Submission docs, transcript, and public positioning were prepared

### Why it mattered

Day 4 was about making the project legible and believable under judging pressure. The work was less about adding random features and more about removing confusion and making the core loop present clearly.

## Final Product State

By the end of the build, Sah.Bukti had:

- FastAPI backend
- SQLite source of truth
- React frontend served through FastAPI
- WhatsApp-style evidence intake
- Review queue for payment proofs
- Approval-driven ledger mutation
- Invoice and customer flows
- Accountant export
- Month-end readiness view

## Final Wedge

Sah.Bukti is not trying to replace WhatsApp.

It is trying to turn messy WhatsApp operations into reviewable business truth.
