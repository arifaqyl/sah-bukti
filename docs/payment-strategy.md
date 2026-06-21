# Sah.Bukti Payment Strategy

Generated: 2026-06-16

## Question Type

- comparison
- product decision
- payment architecture

## Sourced Facts

1. PayNet documents DuitNow Merchant-Presented QR as a flow where the merchant provides a QR code, either static or dynamic, for the customer to scan in a bank or e-payment app.
   Source: https://docs.developer.paynet.my/docs/duitNow-QR/introduction/overview

2. PayNet's Merchant-Presented Domestic QR flow is formal, networked infrastructure involving issuer, RPP, and acquirer steps, plus merchant notification on successful QR payment status.
   Source: https://docs.developer.paynet.my/docs/duitNow-QR/integration/merchant-presented-QR/domestic-QR

3. DuitNow Request officially lets merchants or billers send payment requests that appear in the customer's internet or mobile banking inbox, with a longer expiry period.
   Source: https://docs.developer.paynet.my/docs/duitNow-request/introduction/overview

4. PayNet positions DuitNow Online Banking/Wallets as business checkout that can receive payments from more than 40 banks and eWallets.
   Source: https://www.paynet.my/business-solutions/duitnow-online-banking-wallet.html

5. MyInvois payment mode codes currently include `03 Bank Transfer` and `06 e-Wallet / Digital Wallet`.
   Source: https://sdk.myinvois.hasil.gov.my/codes/payment-methods/

6. MyInvois Invoice v1.0 includes fields for `PaymentMeansCode`, supplier bank account, payment terms, prepaid amount/date/time, and prepayment reference number.
   Source: https://sdk.myinvois.hasil.gov.my/documents/invoice-v1-0/

7. MyInvois states e-Invoice supports B2B, B2C, and B2G flows and is intended to help MSMEs transition progressively.
   Source: https://sdk.myinvois.hasil.gov.my/start/

8. PayNet's FPX merchant guide shows direct FPX integration is not a weekend toggle. It requires choosing an acquirer, registration forms, certificates, testing, UAT, and migration.
   Source: https://www.paynet.my/attachments/business-fpx/FPX_Merchant-Interfacing-Basic-Guide.pdf

## Inference

- For the vibeathon, direct PayNet or raw FPX integration is the wrong level of complexity.
- For low-ticket Malaysian merchants, the strongest wedge is not "accept more payment methods"; it is "make the existing static QR workflow less manual and less scam-prone."
- The payment story should begin with `03 Bank Transfer` and static QR verification, then grow into request and gateway layers later.

## Recommendation

### Tier 1: MVP now

- `duitnow_qr_static`
- invoice records with `payment_mode_code=03`
- screenshot verification
- duplicate reference detection
- auto-mark invoice as paid
- MyInvois-ready export

Why:

- cheapest workflow for small sellers
- easiest to demo
- strongest mismatch with existing generic payment products
- fits your WhatsApp + parsing strength

### Tier 2: Strong next feature

- `DuitNow Request`-style collection workflow
- not direct PayNet integration yet
- simulate request creation inside Sah.Bukti: amount, expiry, note, copied reminder text, pending/expired/paid states

Why:

- closer to real collections than passive QR sharing
- better for overdue invoice chasing
- strong X/demo angle

### Tier 3: Growth mode

- provider toggle for gateway checkout
- likely via gateway/provider abstractions instead of raw PayNet implementation
- use only when merchant ticket size or transaction volume justifies fees

Why:

- cards and managed checkouts matter later, not first
- direct infra cost and compliance are too heavy for hackathon scope

## Anti-Thesis

Do not position the project as:

- "another payment gateway"
- "an all-in-one POS"
- "replace all local rails"

The sharper position is:

- `Sah.Bukti` helps tiny Malaysian merchants stay on zero-fee-ish local habits longer, while making those habits safer and more trackable.

## What Claude Should Challenge

- whether `03 Bank Transfer` is the right default code for static DuitNow QR receipts versus `06 e-Wallet / Digital Wallet` in mixed bank/eWallet cases
- whether invoice matching should require recipient-name checks in addition to amount + reference
- whether a later "request payment" phase should mimic DuitNow Request UX or jump straight to a gateway partner
- whether the target user is better framed as freelancers, food micro-merchants, home bakers, or Instagram sellers
