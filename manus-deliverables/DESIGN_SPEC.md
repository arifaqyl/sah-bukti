# Sah.Bukti — Anti-Slop Design Spec

## Brand
Sah.Bukti = reviewable evidence to approved ledger. Warm, human, paper-and-ink. NOT corporate SaaS. NOT dark fintech.

## Forbidden
- Purple / indigo / violet gradients
- Brass glow / warm brass rings
- Dark void backgrounds (#08080b, #0f0f14, #181820)
- "Server room at midnight" aesthetic
- Generic AI landing page: Inter-only typography, glowing gradient CTAs, mesh hero backgrounds
- SVG texture files

## Required
- Light warm paper background: #F5F1EB or #FBF8F3
- Clay/terracotta accent: #C75B39
- Typography: DM Sans (body) + Fraunces (headings)
- CSS-only surfaces: radial gradients for paper texture
- Motion: staggered fadeUp, gentle float, reduced-motion support
- Mobile-first responsive (min 320px)

## Design Tokens
```css
:root {
  --bg: #FBF8F3;
  --surface: #FFFDF8;
  --ink: #1C1917;
  --muted: #78756E;
  --border: #E7E3DD;
  --accent: #C75B39;
  --accent-hover: #9A3412;
  --success: #15803D;
  --warn: #A16207;
  --danger: #DC2626;
  --chip: #F5F1EB;
  --font-sans: 'DM Sans', system-ui, sans-serif;
  --font-serif: 'Fraunces', Georgia, serif;
  --r-sm: 12px;
  --r-md: 16px;
  --r-lg: 22px;
  --r-pill: 999px;
}
```

## Components
- Cards: white/cream surface, subtle border, gentle shadow
- Buttons: pill shape, ink or accent fill, hover lift
- Inputs: warm border, focus ring in accent
- Badges: pill, semantic colors (success/warn/danger/accent)
- Nav: sticky glass navbar (landing), sidebar (dashboard), bottom tab bar (mobile)

## Motion
- fadeUp: translateY(20px) → 0, opacity 0→1, 600ms ease
- float: translateY(0→-10px) rotate(2deg), 6s infinite
- Stagger delays: d1=0.05s, d2=0.12s, d3=0.19s, d4=0.26s, d5=0.33s
- Reduced motion: disable all animations

## Page Structure
- Landing: hero (copy + phone mockup), stats strip, bento grid, steps, split panels, CTA band
- Auth: 4-step wizard (name → shop → type → color swatch)
- Dashboard: sidebar + topbar + content area + mobile bottom nav
- All other pages: sidebar nav + content area

## File Organization
Multi-page SPA with hash routing:
- /frontend/index.html (landing)
- /frontend/auth.html
- /frontend/dashboard.html
- /frontend/invoices.html
- /frontend/customers.html
- /frontend/inventory.html
- /frontend/evidence.html
- /frontend/review.html
- /frontend/readiness.html
- /frontend/export.html
- /frontend/help.html
- /frontend/profile.html
- /frontend/app.css (design system)
- /frontend/css/*.css (page-specific)
- /frontend/js/auth.js, router.js, dashboard.js, pages/*.js
