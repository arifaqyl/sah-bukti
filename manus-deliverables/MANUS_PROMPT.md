ROLE
You are acting as senior frontend engineer + UI designer for a Malaysian micro-SME product called Sah.Bukti (also written Sah.Bukti).

TASK
Rebuild the existing frontend so it is no longer Codex-generated. Deliver a fully working, single-page web app landing + auth + dashboard shell that looks nothing like generic AI slop. Style must reference the exact style, motion, wording, and material system already in the current new frontend.

GOAL
After switching to the new frontend, every page must feel consistent, human-crafted, warm, tactile, and intentionally designed. No purple gradients. No aesthetic resembling typical AI-generated landing pages.

SOURCES OF TRUTH
Use these exact existing files as the style and behavior reference. Rebuild from scratch in your own files, do NOT copy-paste them.
- DESIGN_SPEC.md  ← the full design spec, naming conventions, and motion taste you must obey
- REFERENCE.zip    ← the current anti-slop implementation (one HTML + one CSS + one JS router)
- BACKEND.md       ← the real backend APIs. Keep all API contracts unchanged.

STYLE MANDATE (non-negotiable)
1. Light, friendly, paper-and-ink aesthetic. Background like warm paper, not blancmange.
2. Clay/terracotta (#C75B39) as primary accent. No default blue. No purple.
3. Typography: DM Sans + Fraunces.
4. "Anti-slop rules" in DESIGN_SPEC.md must be followed exactly.
5. No brass glow. No dark fintech espresso styling.
6. No SVG texture files. Use CSS-only surfaces (radial gradients). No generic vector art.
7. Motion must feel handcrafted: staggered reveal, gentle float, reduced-motion support.
8. Every screen must have a job and a clear next step.

DELIVERABLES
Create a brand-new frontend in /frontend/ with this exact structure:
- /frontend/index.html          (SPA shell)
- /frontend/app.css             (full anti-slop design system)
- /frontend/app.js              (SPA router + auth shell + landing + dashboard)
- /frontend/css/landing.css     (landing layout)
- /frontend/css/auth.css        (wizard + signup)
- /frontend/css/dashboard.css   (app shell + sidebar)
- /frontend/css/motion.css      (animations only)
- /frontend/js/auth.js          (auth logic)
- /frontend/js/router.js        (hash router)
- /frontend/js/dashboard.js     (dashboard page)
- /frontend/js/pages/           (one JS per page: invoices.js, customers.js, inventory.js, evidence.js, review.js, readiness.js, export.js, help.js, profile.js)

EXISTING CODEBASE CONTRACT (preserve exactly)
- All URL routes and API endpoints defined in BACKEND.md must still work.
- Do NOT change any backend API path, request shape, response shape, or auth flow.
- The backend is already running and working. Only the frontend is being replaced.
- Do NOT introduce new API calls, new auth flows, or new required backend endpoints.

MINIMUM VIABLE REQUIREMENTS
- Landing page with hero, bento grid, stat strip, steps, split panels, CTA band.
- Auth wizard: name → shop name → shop type → accent color.
- Dashboard shell with sidebar + mobile bottom nav.
- Every other page must render (not show 404).
- No hardcoded secrets. No dead links. No broken buttons.
- Mobile-first responsive layout (min 320px width).
- Performance target: smooth 60fps on mid-range Android. No layout thrash, no blocking scripts above the fold.

PROHIBITED
- Do not use any purple or indigo gradient as a primary visual.
- Do not reuse Codex-generated component names unchanged in a way that revives the old look.
- Do not include brass glow, dark fintech espresso, "server room at midnight", or any similar aesthetic.
- Do not add new backend features, new API endpoints, or new cookie/session mechanisms.

ACCEPTANCE CRITERIA
1. Opening /frontend/index.html in a browser renders the landing page visually.
2. Clicking "Start free" opens the auth wizard with all 4 steps.
3. Completing signup transitions to the dashboard shell.
4. Sidebar + mobile bottom nav work and switch pages.
5. Every route from /dashboard to /help renders real content (not blank).
6. Visual inspection confirms the design is NOT generic AI slop.
7. DevTools console shows zero JS errors on each route.

DELIVERY FORMAT
Produce a zipped deliverable named:
Sah.Bukti_anti_slop_frontend_rebuild.zip
Root folder inside zip: /kedai-frontend-rebuild/
Include a short README.md inside that zip:
- How to run
- What files were created
- Known limitations
- Notes for handoff back to the original repo

WORKFLOW
1. Read DESIGN_SPEC.md, REFERENCE.zip, and BACKEND.md.
2. Scaffold the exact file structure above.
3. Implement CSS first (design tokens, layout, components, motion, responsive).
4. Implement JS router and auth shell.
5. Implement each page module under js/pages/.
6. Verify locally (explain what you tested and what passed).
7. Zip the /kedai-frontend-rebuild/ folder.
8. Return the zip plus a 1-paragraph summary of what you changed.
