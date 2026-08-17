# Guest Snap R2-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify guest photo collection to private R2 storage protected by Turnstile, without collecting names or operating D1, a public gallery, or an admin page.

**Architecture:** The React form sends optimized images directly to one Pages Function. The Function enforces the opening date, validates Turnstile and image constraints, and writes each object under a date-based private R2 key. Photos are reviewed and downloaded from the Cloudflare R2 dashboard rather than through application APIs.

**Tech Stack:** React 19, TypeScript, Vite, Cloudflare Pages Functions, Cloudflare R2, Cloudflare Turnstile, Vitest.

---

### Task 1: Define the R2-only upload contract

**Files:**
- Modify: `wedding-invitation/src/components/GuestSnap.test.tsx`
- Modify: `wedding-invitation/functions/api/guest-snap/photos.test.ts`

- [ ] Remove name, message, gallery, D1, and rate-limit expectations from the tests.
- [ ] Assert that the browser submits only `photo` and `turnstileToken`.
- [ ] Assert that the Function stores a validated image in R2 with upload metadata.
- [ ] Run the focused tests and confirm they fail against the D1-backed implementation.

### Task 2: Simplify the client and upload Function

**Files:**
- Modify: `wedding-invitation/src/components/GuestSnap.tsx`
- Modify: `wedding-invitation/functions/api/guest-snap/photos.ts`
- Modify: `wedding-invitation/functions/api/guest-snap/_shared.ts`
- Modify: `wedding-invitation/src/main.tsx`

- [ ] Remove personal text inputs, gallery loading, image viewer state, and admin routing.
- [ ] Keep date gating, file optimization, Turnstile, progress, and upload status.
- [ ] Remove D1 and admin-secret types and retain only private R2 upload dependencies.
- [ ] Run focused tests and confirm the new contract passes.

### Task 3: Delete obsolete D1 and moderation surfaces

**Files:**
- Delete: `wedding-invitation/src/components/GuestSnapAdmin.tsx`
- Delete: `wedding-invitation/src/components/GuestSnapAdmin.test.tsx`
- Delete: `wedding-invitation/functions/api/guest-snap/admin/`
- Delete: `wedding-invitation/functions/api/guest-snap/media/`
- Delete: `wedding-invitation/migrations/0001_guest_snap.sql`
- Modify: `wedding-invitation/src/index.css`

- [ ] Delete admin, media-serving, migration, and related test files.
- [ ] Remove unused admin, form-field, and guest-gallery styles.
- [ ] Search the project and confirm no D1 or admin references remain.

### Task 4: Document and verify Cloudflare setup

**Files:**
- Modify: `wedding-invitation/README.md`

- [ ] Document the `GUEST_SNAP_BUCKET` R2 binding.
- [ ] Document `VITE_TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, and `GUEST_SNAP_UPLOAD_OPENS_AT`.
- [ ] State that the R2 bucket must remain private and photos are managed in the R2 dashboard.
- [ ] Run all tests, build, lint, Functions type-check, and Wrangler Functions compilation.
