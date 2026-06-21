# Kracked Devs Vibe-a-thon Build Note

## Why this project exists

Sah.Bukti was built for the Kracked Devs Vibe-a-thon around a narrow operational pain:

small sellers already work in WhatsApp, but payment proof, order details, and month-end records stay messy for too long.

The project goal was to turn that operational mess into:

- structured evidence
- explicit review
- owner-approved ledger updates
- cleaner accountant handoff

## Why this repo keeps build notes

This repository is not meant to be a generic polished startup skeleton with all build history erased.

It is a real shipped hackathon build that has been cleaned for public viewing while still preserving:

- the product rationale
- the architecture choices
- the trust boundary decisions
- the specific scope cuts that kept it believable

## Main build constraints

- keep WhatsApp as the workflow, not the database
- never allow inbound evidence to auto-confirm payment truth
- avoid ERP drift
- avoid generic AI assistant positioning
- stay demoable in a short time window without faking the ledger

## What was intentionally prioritized

- payment proof review gate
- invoice and evidence flow coherence
- month-end and accountant export payoff
- public repo safety
- public deployment safety

## What was intentionally de-prioritized

- broad platform integrations
- public self-serve connector administration
- full accounting-suite depth
- generic conversational AI behavior

## What this means for the repo

The documentation should help a visitor understand:

1. what problem Sah.Bukti solves
2. why the trust boundary matters
3. how to run it locally
4. which parts are core product versus optional local tooling
