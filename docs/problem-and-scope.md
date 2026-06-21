# Problem and Scope

## Problem

Many Malaysian micro-sellers already run their business inside WhatsApp. Orders, payment claims, screenshots, follow-up, and handoff to an accountant happen across chat, memory, and spreadsheets.

That creates three failures:

- order and payment evidence gets buried in chat
- payment truth is assumed too early
- month-end handoff becomes manual cleanup

## Product Response

Sah.Bukti does not try to replace WhatsApp.

It creates a control plane behind that workflow:

- capture order or payment evidence
- normalize it into structured records
- hold payment claims in review
- let the owner approve what is true
- export cleaner financial records after approval

## Product Scope

In scope:

- order text intake
- payment-proof intake
- review queue
- owner approval and rejection
- invoice and customer records
- accountant export
- month-end readiness and provision reporting

Out of scope:

- full accounting suite behavior
- autonomous payment confirmation
- generic chatbot use cases
- ERP-style module sprawl
- public self-serve connector administration
