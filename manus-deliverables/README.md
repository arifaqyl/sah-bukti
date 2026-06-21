# Sah.Bukti — Manus AI Build Package

## What is this
Everything Manus AI needs to rebuild your frontend as a brand new anti-slop app.

## Files
- `MANUS_PROMPT.md` — the exact prompt to paste into Manus. It includes role, task, style mandate, deliverables, API contract, acceptance criteria, and workflow.
- `REFERENCE_app.css` — the current anti-slop design system. Style tokens, layout, components, bento, auth, dashboard, motion, responsive breakpoints.
- `REFERENCE_app.js` — the current SPA router + page templates. Keep the routing pattern, page names, and `<div id="page-content">` contract.
- `REFERENCE_index.html` — minimal SPA shell showing expected load order.
- `BACKEND_API_MAP.md` — real FastAPI routes and request/response shapes. Your new frontend must call these exactly; do not invent new endpoints.

## How to use
1. Open Manus (manus.im).
2. Paste the content of `MANUS_PROMPT.md` as the first message.
3. Attach all 4 files (REFERENCE_* + BACKEND_API_MAP.md) in the same message.
4. Wait for Manus to return `Sah.Bukti_anti_slop_frontend_rebuild.zip`.
5. Unzip and review `/kedai-frontend-rebuild/`.
6. Replace `/frontend/` with the new folder contents.
7. Run backend + open `/frontend/index.html`.

## Notes
- The backend is already running and working. Do not change it.
- All auth uses Bearer tokens from `/api/v1/auth/login` or `/signup`.
- The design system mandates: no purple/indigo, no brass glow, no dark fintech espresso. Clay/terracotta accent on warm paper.
- Keep the hash router (`#/dashboard`, `#/invoices`, etc.) so existing bookmark style links still work.
