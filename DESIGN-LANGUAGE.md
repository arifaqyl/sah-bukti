# Kede — Design Language Reference

**Version:** 1.0  
**Date:** 2026-06-18  
**Context:** Dark mobile dashboard for Malaysian micro-SMEs  
**Audience:** Codex / Claude Code — read this before building any frontend

---

## 1. Brand Personality

Kede is NOT a sterile corporate dashboard. It's a warm, artisanal tool for a baker who wakes up at 4am and an accountant who works late nights.

**Keywords:** Warm brass, morning light, charcoal warmth, craft precision, readable at 1am, Malaysian small-business soul.

**Forbidden associations:** Cold fintech blue, sterile SAS SaaS, purple gradients, Inter on white, generic "AI dashboard" feel.

---

## 2. Color System

### 2.1 Primary Palette

| Role | Token | Value | Usage |
|------|-------|-------|-------|
| Background deepest | `--bg-void` | `#08080b` | Body background, deepest layer |
| Background default | `--bg-primary` | `#0f0f14` | Cards, panels |
| Background elevated | `--bg-elevated` | `#181820` | Hovered cards, inputs |
| Background overlay | `--bg-overlay` | `#1e1e2a` | Modals, dropdowns |

### 2.2 Accent — Warm Brass

| Role | Token | Value | Usage |
|------|-------|-------|-------|
| Accent primary | `--accent` | `#d4a853` | Primary CTA, provision highlight, active states |
| Accent hover | `--accent-hover` | `#e6bc6a` | Hover states |
| Accent soft | `--accent-soft` | `rgba(212, 168, 83, 0.12)` | Glow rings, selected backgrounds |
| Accent muted | `--accent-muted` | `rgba(212, 168, 83, 0.5)` | Disabled states, placeholders |

**Why brass, not blue?**
- Baker context: golden crust, morning warmth
- Avoids the banned 200-290 hue band (blue-indigo-violet)
- Reads as premium but not cold
- One voltage: brass is the only saturation in the system

### 2.3 Semantic Colors

| Role | Token | Value | Usage |
|------|-------|-------|-------|
| Success | `--success` | `#4ade80` | Paid, positive cashflow |
| Warning | `--warning` | `#fbbf24` | Overdue, low stock |
| Danger | `--danger` | `#f87171` | Critical overdue, errors |
| Info | `--info` | `#60a5fa` | Current invoices, informational |

### 2.4 Text Hierarchy (3 levels minimum)

| Role | Token | Value | Usage |
|------|-------|-------|-------|
| Text primary | `--text-primary` | `#f5f0e8` | Headings, important numbers |
| Text secondary | `--text-secondary` | `#a09b8f` | Body text, labels |
| Text muted | `--text-muted` | `#6b665c` | Timestamps, helper text |
| Text on accent | `--text-on-accent` | `#0f0f14` | Text on brass buttons |

### 2.5 Border & Surface Separation

| Role | Token | Value | Usage |
|------|-------|-------|-------|
| Border default | `--border` | `#2a2a32` | Default card borders |
| Border strong | `--border-strong` | `#3a3a45` | Input focus, active elements |
| Border accent | `--border-accent` | `rgba(212, 168, 83, 0.3)` | Accent-bordered cards |

### 2.6 Selection & Focus

| Role | Token | Value | Usage |
|------|-------|-------|-------|
| Selection | `--selection-bg` | `rgba(212, 168, 83, 0.3)` | Custom text selection |
| Focus ring | `--focus-ring` | `rgba(212, 168, 83, 0.5)` | Keyboard focus |

---

## 3. Typography

### 3.1 Font Stack

| Role | Family | Weights | Fallback |
|------|--------|---------|----------|
| Display | **Cormorant Garamond** | 500, 600, 700 | Georgia, serif |
| Body | **Outfit** | 300, 400, 500, 600 | system-ui, sans-serif |
| Mono | **JetBrains Mono** | 400, 500 | monospace |

**Why these?**
- Cormorant Garamond: Warm serif with old-style figures. Feels crafted, not corporate. Use for brand name, page titles, hero numbers.
- Outfit: Modern geometric sans, NOT Inter. Clean but has more personality. Humanist feel.
- JetBrains Mono: For numbers, currency, invoice IDs. Tabular figures essential.

**NEVER ship Inter, system-ui alone, or bare sans-serif.**

### 3.2 Type Scale

Base size: 16px. Scale ratio: 1.25 (major third).

| Token | Size | Line Height | Usage |
|-------|------|-------------|-------|
| `--text-xs` | 0.75rem (12px) | 1.4 | Helper text, timestamps |
| `--text-sm` | 0.875rem (14px) | 1.5 | Labels, secondary text |
| `--text-base` | 1rem (16px) | 1.6 | Body text, inputs |
| `--text-lg` | 1.25rem (20px) | 1.5 | Card titles, section headers |
| `--text-xl` | 1.5rem (24px) | 1.3 | Page titles |
| `--text-2xl` | 2rem (32px) | 1.2 | Dashboard hero numbers |
| `--text-3xl` | 2.5rem (40px) | 1.1 | Brand name |
| `--text-4xl` | 3.5rem (56px) | 1.05 | Provision hero amount |

### 3.3 Typography Rules (enforced)

- **NEVER** set all headings to weight 700. Use: h1=700, h2=600, h3=500.
- **ALWAYS** use `text-wrap: balance` on headings.
- **ALWAYS** tighten display text: `letter-spacing: -0.02em` on h1-h3.
- **ALWAYS** run heading line-height tight (1.1-1.4), body loose (1.5-1.7).
- **ALWAYS** use JetBrains Mono for numbers and currency.
- **ALWAYS** load fonts with `preconnect` to Google Fonts.

---

## 4. Spacing & Layout

### 4.1 Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Icon-text gaps, tight inline |
| `--space-sm` | 8px | Button padding, list gaps |
| `--space-md` | 16px | Card padding, section gaps |
| `--space-lg` | 24px | Page edge padding (tablet) |
| `--space-xl` | 32px | Section dividers |
| `--space-2xl` | 48px | Hero padding top |
| `--space-3xl` | 64px | Hero padding desktop |

### 4.2 Layout Rules (enforced)

- **NEVER** use `grid-template-columns: repeat(3, 1fr)` for cards. Use `2fr 1fr`, `3fr 2fr`, or asymmetric splits.
- **NEVER** center everything. Left-align at least one section per view.
- **ALWAYS** give hero noticeably more vertical padding than content sections.
- **ALWAYS** collapse to single column on mobile (320px+).
- **ALWAYS** vary gap by relationship: related items = tight (8px), sections = loose (24px).
- **ALWAYS** define at least 3 section padding variants.

### 4.3 Max Widths

| Context | Value |
|---------|-------|
| Dashboard content | `960px` |
| Form inputs | `100%` max `480px` |
| Provision table | `100%` |

**NEVER default to max-w-7xl (1280px).**

---

## 5. Component Design Rules

### 5.1 Border Radius

| Element | Token | Value |
|---------|-------|-------|
| Buttons | `--radius-btn` | 6px |
| Cards | `--radius-card` | 10px |
| Inputs | `--radius-input` | 8px |
| Containers | `--radius-container` | 14px |
| Badges | `--radius-badge` | 100px (pill) |

**NEVER use 8px everywhere. Vary by element purpose.**

### 5.2 Shadows / Elevation

Kede uses layered surface separation, not generic shadows.

| Level | Token | Usage |
|-------|-------|-------|
| Elevation 1 | `--shadow-1` | Cards on primary bg |
| Elevation 2 | `--shadow-2` | Elevated cards, dropdowns |
| Elevation 3 | `--shadow-3` | Modals, overlays |

```css
--shadow-1: 0 1px 2px rgba(0,0,0,0.4), 0 0 0 1px var(--border);
--shadow-2: 0 4px 12px rgba(0,0,0,0.5), 0 0 0 1px var(--border);
--shadow-3: 0 12px 40px rgba(0,0,0,0.6), 0 0 0 1px var(--border-strong);
```

**NEVER stamp identical shadows.** Use border for elevation when appropriate.

### 5.3 Buttons

Three variants with real visual distance:

| Variant | Style | Usage |
|---------|-------|-------|
| Primary | Brass fill, dark text | Main CTA, "Create Invoice", "Calculate" |
| Secondary | Border, light text | Secondary actions, "Cancel", "Back" |
| Ghost | Transparent, accent text on hover | Tertiary, "Edit", icon buttons |

**NEVER make all buttons identical.**

### 5.4 Cards

All content lives inside cards. Never directly on page background.

| Card Type | Style |
|-----------|-------|
| Default | `--bg-primary`, `--border`, `--shadow-1` |
| Elevated | `--bg-elevated`, `--border-strong`, `--shadow-2` |
| Accent-bordered | `--bg-primary`, `--border-accent`, subtle brass glow |
| Provision hero | `--bg-primary`, gradient brass border-top, `--shadow-2` |

**Card vs background contrast IS the separator.** Don't rely on borders alone.

### 5.5 Badges & Status

| Status | Background | Text |
|--------|-----------|------|
| Pending | `rgba(251, 191, 36, 0.15)` | `--warning` |
| Paid | `rgba(74, 222, 128, 0.15)` | `--success` |
| Overdue | `rgba(248, 113, 113, 0.15)` | `--danger` |
| Partial | `rgba(96, 165, 250, 0.15)` | `--info` |

---

## 6. Motion & Animation

### 6.1 Easing Curve

```css
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
--ease-in-out: cubic-bezier(0.22, 1, 0.36, 1);
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
```

**NEVER use generic `ease-in-out` on interactive elements.**
**NEVER write `transition: all`.** Always name properties.

### 6.2 Duration

| Context | Duration |
|---------|----------|
| Hover / focus | 150ms |
| Button press | 100ms |
| Card hover | 200ms |
| Page transition | 300ms |
| Modal enter | 250ms |
| Stagger reveal | 80ms per item |

### 6.3 Motion Rules (enforced)

- **NEVER** animate `width`, `height`, `top`, `left`. Use `transform` + `opacity`.
- **ALWAYS** respect `prefers-reduced-motion: reduce`.
- **NEVER** use `animate-pulse` or `animate-bounce` on content. Reserve for loading states only.
- **ALWAYS** use different easing for enter vs exit.
- **NEVER** use `fade-in-up` as the only animation. It's motion slop.

### 6.4 Page Transitions

```css
.page-enter {
  opacity: 0;
  transform: translateY(8px);
}
.page-enter-active {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 300ms var(--ease-out), transform 300ms var(--ease-out);
}
```

---

## 7. The Provision Page — The Climax

This is the most important page. It's the demo moment. Design it with extra care.

### 7.1 Visual Hierarchy

```
┌─────────────────────────────────┐
│  Month-End Provision            │ ← --text-lg, --text-secondary
│                                 │
│  RM 2,400.00                    │ ← --text-4xl, --accent, Cormorant Garamond
│  Based on 23 outstanding        │ ← --text-sm, --text-muted
│                                 │
│  ┌──────┬──────┬──────┬──────┐  │
│  │ 30d  │ 60d  │ 90d  │180+ │  │ ← Asymmetric aging breakdown
│  │ 5%   │ 10%  │ 20%  │ 100%│  │
│  └──────┴──────┴──────┴──────┘  │
│                                 │
│  Journal Entry                  │ ← --text-lg
│  ┌─────────────────────────┐    │
│  │ Dr Provision      RM2,400│    │ ← --danger color for debit
│  │ ─────────────────────── │    │ ← border separator
│  │ Cr Allowance      RM2,400│    │ ← --success color for credit
│  │ ✓ Balanced              │    │ ← --text-muted, --success
│  └─────────────────────────┘    │
│                                 │
│  [Export CSV]  [Export JSON]    │ ← --space-md gap, not centered
└─────────────────────────────────┘
```

### 7.2 The Big Number

- Size: `--text-4xl` (56px on desktop, 40px mobile)
- Font: Cormorant Garamond 700
- Color: `--accent`
- No glow, no gradient text. Let the brass color do the work against the charcoal.

### 7.3 Aging Breakdown

- Use a 2×2 grid, NOT a 4-column equal grid
- Each cell shows: bucket name, count, amount, rate
- Vary visual weight: 180+ bucket should feel heavier (it's the scariest number)

### 7.4 Journal Entry

- Deep inset panel (`--bg-overlay`)
- Debit in danger red, credit in success green
- Separator is a single border line
- "Balanced" indicator is small, muted, reassuring

---

## 8. Accessibility (enforced)

- **ALWAYS** use semantic HTML (`<main>`, `<nav>`, `<section>`, `<header>`).
- **ALWAYS** provide `:focus-visible` ring in `--focus-ring`.
- **ALWAYS** set custom `::selection` background in `--selection-bg`.
- **ALWAYS** maintain 4.5:1 contrast for body, 3:1 for large text.
- **ALWAYS** include `prefers-reduced-motion` handling.
- **NEVER** skip `alt` text. Use `alt=""` for decorative images only.
- **NEVER** reuse one meta description per route.

---

## 9. What Makes This NOT "AI Slop"

| AI Slop Pattern | Kede Decision |
|-----------------|---------------|
| Pure `#ffffff` / `#000000` | Tinted backgrounds (`#0f0f14`, `#f5f0e8`) |
| Blue-indigo-violet primary | Warm brass `#d4a853` |
| Inter on white | Cormorant Garamond + Outfit on charcoal |
| `repeat(3, 1fr)` cards | Asymmetric splits, 2×2 variant grids |
| Same padding everywhere | 4px-xs, 16px-md, 48px-hero, 64px-desktop-hero |
| `transition: all` | Named properties: `transform`, `opacity`, `color` |
| Hover scale + shadow on cards | Subtle border color shift + brass glow |
| `rounded-lg` on everything | 6px/8px/10px/14px by element purpose |
| Fade-up on scroll | Staggered reveal with offset, different easing |
| 3 identical CTA buttons | Context-specific copy: "Add Invoice", "View Aging", "Export" |
| Generic purple gradient hero | Brass accent line + warm charcoal depth |
| No print stylesheet | **Add one.** |

---

## 10. Font Loading

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=JetBrains+Mono:wght@400;500&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">
```

**NEVER load more than 3 families. ALWAYS use `preconnect`.**

---

## 11. Directory Structure

```
frontend/
├── tokens.css          # CSS custom properties (this design system)
├── index.html          # SPA entry
├── css/
│   ├── reset.css       # Minimal reset
│   ├── base.css        # Base element styles
│   ├── components.css  # Buttons, cards, badges, inputs
│   ├── pages.css       # Page-specific layouts
│   └── motion.css      # Animations + transitions
├── js/
│   ├── api.js          # API client
│   ├── router.js       # Hash router
│   ├── app.js          # App init
│   ├── dashboard.js    # Home page
│   ├── invoices.js     # Invoice list + detail
│   ├── inventory.js    # Inventory view
│   └── provision.js    # Provision calculator (THE PAGE)
```

---

## 12. Design Review Checklist

Before shipping any page, verify:

- [ ] Primary hue is NOT in 200-290 range (no blue-indigo-violet)
- [ ] Background is NOT pure `#ffffff` or `#000000`
- [ ] At least 3 text hierarchy levels present
- [ ] No `transition: all` anywhere
- [ ] No `rounded-lg` on everything (vary radii)
- [ ] Hero padding is distinct from content padding
- [ ] At least one section is left-aligned or asymmetric
- [ ] Fonts loaded with `preconnect`
- [ ] `text-wrap: balance` on headings
- [ ] Custom `::selection` color set
- [ ] `:focus-visible` ring implemented
- [ ] `prefers-reduced-motion` respected
- [ ] Content width is specific (960px), not `max-w-7xl`
- [ ] Cards have visual separation from background (not just borders)

---

## 13. References

- Sailop Anti-Slop Manifesto: https://sailop.com/blog/anti-slop-manifesto-73-rules-for-unique-design
- StyleSeed Engine: https://github.com/bitjaru/styleseed
- Adminator v4: https://github.com/puikinsh/Adminator-admin-dashboard
- JasonColapietro/anti-slop-templates: https://github.com/JasonColapietro/anti-slop-templates
- Mercury Design System (Google Labs): https://www.shadcn.io/design/mercury
- Claude Cookbook — Frontend Aesthetics: https://platform.claude.com/cookbook/coding-prompting-for-frontend-aesthetics

---

**Last rule:** When in doubt, make it feel like a warm kitchen at 4am, not a server room at midnight.
