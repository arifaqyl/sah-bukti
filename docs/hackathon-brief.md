# Sah.Bukti Hackathon Brief

## Event fit

From the event page you pasted:

- build window: June 17, 2026 10:00 PM GMT+8 to June 21, 2026 9:59 PM GMT+8
- theme: messy, repetitive, manual workflows for small teams and small businesses
- submission needs a project name, one-sentence problem statement, demo, live link or GitHub link, build thread, and AI tools used
- daily progress on X must tag `@KrackedDevs` and use `#KrackedDevsVibeathon`

## Current Malaysia signal

### Sourced facts

1. SME Corp says MSMEs accounted for `96.1%` of all business establishments in Malaysia in 2024.
   Source: https://www.smecorp.gov.my/index.php/en/policies/2020-02-11-08-01-24/profile-and-importance-to-the-economy

2. LHDN's e-Invoice implementation timeline says businesses with annual turnover or revenue of up to `RM5 million` start on `January 1, 2026`, while taxpayers under `RM1,000,000` are exempted.
   Source: https://www.hasil.gov.my/en/e-invoice/implementation-of-e-invoicing-in-malaysia/e-invoice-implementation-timeline/

3. The MyInvois SDK shows there is already an API path for document types and document submission, so "e-Invoice-ready export" is a credible MVP direction even if full submission is out of scope.
   Sources:
   - https://sdk.myinvois.hasil.gov.my/api/
   - https://sdk.myinvois.hasil.gov.my/einvoicingapi/02-submit-documents/

### Inference

- Malaysia has a huge MSME base.
- Kracked Devs wants ops pain, not novelty demos.
- E-invoice pressure makes invoice hygiene and customer record quality more urgent than a generic assistant.
- A reviewable evidence and collections tool is local enough to feel real and broad enough to demo fast.

## Recommendation

Build `Sah.Bukti`:

- a FastAPI + SQLite ops tool
- for WhatsApp-heavy Malaysian freelancers and small businesses
- focused on invoices, follow-ups, and e-Invoice-ready records

## One-sentence problem statement

Small Malaysian businesses often manage invoices and payment follow-ups through WhatsApp chats and memory, which leads to missed payments, duplicated work, and poor e-Invoice readiness.

## X angles

1. "building a tiny ops OS for the kind of malaysia small biz that runs on whatsapp and memory"
2. "the problem is not lack of software, it's that the workflow still lives in chat screenshots"
3. "trying to make invoicing less chaotic without turning this into bloated ERP nonsense"
