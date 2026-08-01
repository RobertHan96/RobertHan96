# Mobile Wedding Invitation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile-first Botanical Letter wedding invitation for 한영신 and 이다예 that runs locally and builds as a static Cloudflare Pages site.

**Architecture:** Add an isolated `wedding-invitation/` Vite React application inside the repository. Keep all content in one typed config, keep interaction helpers testable, and render missing transportation, account, RSVP, map-link, and Kakao settings as explicit preparation states rather than fake data.

**Tech Stack:** React, TypeScript, Vite, Tailwind CSS Vite plugin, Vitest, Testing Library, CSS IntersectionObserver animations.

---

### Task 1: Scaffold and test harness

**Files:**
- Create: `wedding-invitation/package.json`
- Create: `wedding-invitation/vite.config.ts`
- Create: `wedding-invitation/src/test/setup.ts`
- Create: `wedding-invitation/src/smoke.test.tsx`

- [ ] Create the React TypeScript Vite app and install Tailwind, Vitest, jsdom, and Testing Library.
- [ ] Configure the Tailwind Vite plugin, Vitest jsdom environment, `es2019` build target, and `npm run test` script.
- [ ] Add a failing smoke test that expects the wedding app root text.
- [ ] Run `npm test -- --run` and confirm failure because the app content is not implemented.

### Task 2: Typed wedding config and date helpers

**Files:**
- Create: `wedding-invitation/src/types/wedding.ts`
- Create: `wedding-invitation/src/config/wedding.ts`
- Create: `wedding-invitation/src/lib/date.ts`
- Create: `wedding-invitation/src/lib/date.test.ts`

- [ ] Write tests for D-Day before, on, and after `2026-11-15T15:50:00+09:00` and for the November 2026 calendar grid.
- [ ] Run the date tests and confirm they fail because helpers are missing.
- [ ] Implement `formatDday()` and `buildCalendarWeeks()` and add the complete provided wedding data to one config object.
- [ ] Run the date tests and confirm they pass.

### Task 3: Botanical content sections

**Files:**
- Create: `wedding-invitation/src/components/Hero.tsx`
- Create: `wedding-invitation/src/components/Invitation.tsx`
- Create: `wedding-invitation/src/components/Couple.tsx`
- Create: `wedding-invitation/src/components/SectionHeading.tsx`
- Modify: `wedding-invitation/src/App.tsx`
- Create: `wedding-invitation/src/App.test.tsx`

- [ ] Write tests asserting both names, invitation copy, venue, family names, and telephone/SMS links.
- [ ] Run the app test and confirm it fails because the sections are absent.
- [ ] Implement Hero, Invitation, and Couple using only config data and semantic links.
- [ ] Run the app and smoke tests and confirm they pass.

### Task 4: Gallery and fullscreen viewer

**Files:**
- Create: `wedding-invitation/src/components/Gallery.tsx`
- Create: `wedding-invitation/src/components/ImageViewer.tsx`
- Create: `wedding-invitation/src/components/Gallery.test.tsx`

- [ ] Write tests for two baby images, coming-soon copy, viewer open/close, and next-image navigation.
- [ ] Run the gallery tests and confirm failure because gallery components are absent.
- [ ] Implement a dialog-based viewer with buttons, Escape, arrow keys, and horizontal swipe threshold handling.
- [ ] Run the gallery tests and confirm they pass.

### Task 5: Date, location, pending sections, and sharing

**Files:**
- Create: `wedding-invitation/src/components/WeddingDay.tsx`
- Create: `wedding-invitation/src/components/Location.tsx`
- Create: `wedding-invitation/src/components/PendingDetails.tsx`
- Create: `wedding-invitation/src/components/Share.tsx`
- Create: `wedding-invitation/src/lib/clipboard.ts`
- Create: `wedding-invitation/src/components/Details.test.tsx`

- [ ] Write tests for selected wedding date, venue address, map image, address copy action, three preparation states, and disabled Kakao guidance.
- [ ] Run the details tests and confirm failure because these sections are absent.
- [ ] Implement the calendar, address and link-copy actions, map viewer, pending sections, and footer.
- [ ] Run the details and app tests and confirm they pass.

### Task 6: Assets, Botanical styling, and metadata

**Files:**
- Create: `wedding-invitation/public/images/baby/groom.jpeg`
- Create: `wedding-invitation/public/images/baby/bride.jpeg`
- Create: `wedding-invitation/public/images/location/map.jpeg`
- Modify: `wedding-invitation/src/index.css`
- Modify: `wedding-invitation/index.html`

- [ ] Copy the three supplied images without recompression.
- [ ] Add the responsive ivory paper layout, botanical SVG ornament styles, arch photos, safe areas, 44px controls, reveal animation, reduced-motion mode, and desktop centered canvas.
- [ ] Add Korean title, viewport, theme color, Open Graph title/description/image, and social-card metadata.
- [ ] Run tests and build to catch missing paths or CSS pipeline failures.

### Task 7: Local run and mobile QA

**Files:**
- Create: `wedding-invitation/README.md`

- [ ] Document `npm install`, `npm run dev`, `npm test -- --run`, `npm run lint`, `npm run build`, and Cloudflare Pages root/build/output settings.
- [ ] Run the full tests, ESLint, TypeScript build, and production build.
- [ ] Start the Vite server and inspect 390px mobile plus desktop layouts.
- [ ] Verify no console errors, no horizontal overflow, gallery navigation, copy feedback, calendar highlight, and preparation states.
- [ ] Commit only wedding invitation files and implementation documentation on the feature branch.

### Task 8: Kakao Talk sharing

**Files:**
- Create: `wedding-invitation/src/lib/kakao.ts`
- Create: `wedding-invitation/src/lib/kakao.test.ts`
- Create: `wedding-invitation/src/types/kakao.d.ts`
- Modify: `wedding-invitation/src/components/Share.tsx`
- Modify: `wedding-invitation/src/components/Details.test.tsx`
- Modify: `wedding-invitation/src/config/wedding.ts`
- Modify: `wedding-invitation/src/types/wedding.ts`
- Modify: `wedding-invitation/index.html`

- [ ] Add failing tests for SDK initialization, the feed template payload, the configured share URL, and the disabled-key state.
- [ ] Run the focused tests and confirm they fail because the Kakao helper is absent.
- [ ] Add the Kakao SDK global type, initialize the SDK once, and call `Kakao.Share.sendDefault()` with the wedding feed template.
- [ ] Connect the existing button to the helper and copy the deployment URL when SDK sharing fails.
- [ ] Add the official SDK `2.8.1` script with SRI and change Open Graph URLs to absolute deployment URLs.
- [ ] Run all tests, lint, and production build, then verify the active and missing-key button states.
