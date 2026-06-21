# Sah.Bukti — Design Brief (Anti-Slop Rebuild)

This project is a **reference-driven rebuild**. The ground-truth spec comes from the provided `DESIGN_SPEC`, `REFERENCE_app.css/js`, and `BACKEND_API_MAP.md`. Fidelity to the "anti-slop" mandate OVERRIDES generic design suggestions. This is the chosen, locked approach — no alternative explorations.

## Brand Essence
Sah.Bukti — reviewable evidence to approved ledger. It turns shop chaos (WhatsApp orders, receipts, payment screenshots) into reviewed, accountant-ready records. Personality: **warm, grounded, trustworthy.**

## Design Movement
Editorial "Paper & Ink" — a tactile, warm-paper aesthetic that feels like a well-designed printed ledger rather than a SaaS dashboard. Inspired by independent print magazines and stationery design.

## Core Principles
1. **Warm paper, not blancmange.** The background is a warm cream (`#F5F1EB`), surfaces are a touch lighter (`#FDFBF7`). Subtle CSS grain only — no SVG texture files.
2. **Clay over blue.** The single ownable accent is clay/terracotta (`#C75B39`). Absolutely no blue, purple, indigo, or brass glow.
3. **Every screen has a job.** Each view states its purpose and offers one clear next step.
4. **Handcrafted motion.** Staggered reveals, gentle float, snappy button feedback, full reduced-motion support.

## Color Philosophy
A warm, ink-on-paper palette. Deep near-black ink (`#1A1A1A`) for text and primary buttons, earthy muted brown (`#8A7F72`) for secondary text, clay terracotta as the one expressive accent. Status colors are muted and earthy (forest green, ochre, brick red) — never neon.

## Layout Paradigm
Asymmetric and editorial. The landing hero is a 1.2fr / 0.8fr split with a floating phone mockup. The dashboard uses a persistent left sidebar (desktop) and a bottom nav (mobile). Avoid dead-centered full-page layouts.

## Signature Elements
- **The clay "K" mark** — a rounded-square logotile in terracotta.
- **Bento grid** with mixed column spans for the feature section.
- **Floating phone mockup** showing real evidence-review microcopy.

## Typography System
- **Fraunces** (serif, opsz) for all headings and statistics — gives an editorial, crafted voice.
- **DM Sans** for body, labels, and UI — clean and friendly.
- Headings use tight tracking (`-0.02em`); overlines use wide uppercase tracking.

## Brand Voice
Direct, shopkeeper-friendly, lightly bilingual (Malay touches like "Selamat Datang"). CTAs are concrete: "Create your shop", "See how it works". Banned: "Welcome to our website", "Get started today".

## Signature Brand Color
Clay / Terracotta `#C75B39`.

## Style Decisions
- No purple/indigo gradients, no brass glow, no dark fintech espresso.
- CSS-only surfaces (radial/dot grain), no generic vector art.
- Radii 16–28px on cards, pill buttons.
