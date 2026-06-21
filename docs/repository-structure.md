# Repository Structure

## Why the repo is split this way

Sah.Bukti is a backend-first product with a committed built frontend.

That means the repository intentionally contains both:

- source code used for development
- built assets used by the FastAPI app in deployment

## Main directories

### `app/`

Core FastAPI application:

- `api/routes/` HTTP routes
- `schemas/` request and response models
- `services/` business logic
- `db/` schema initialization and data access helpers

### `client/`

React and Vite frontend source workspace.

- `client/src/` application UI code
- `server/` frontend-side server bundle entry
- `dist/public/` build output generated during frontend build

This workspace uses `pnpm`.

### `frontend/`

Built frontend files served by FastAPI.

This is the deployed web surface that the backend returns at `/frontend/` and `/`.

### `docs/`

Product-facing and engineering-facing documentation:

- product scope
- architecture
- trust boundary
- repo structure

### `scripts/`

Local helpers only.

This includes optional bridge or seeding utilities. These are not the product itself.

### `tests/`

Backend regression suite for the approval gate, evidence flow, exports, reminders, and month-end logic.

## Important distinction

### Root `package.json`

This is not the main application package.

It exists for the optional local WhatsApp bridge only.

### `client/package.json`

This is the real frontend workspace package file.

If you are building the UI, this is the one you use.
