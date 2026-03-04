# UI/UX Audit — Wave 1 (2026-03-04)

Audit of dotmac_starter templates, components, and static assets.

## P0 — Critical (Blocks Usability)

### P0-1: Missing `scope="col"` on Table Headers
**Files:** `admin/components/table_macros.html`, `admin/settings/list.html`, `index.html`
**Issue:** `<th>` elements lack `scope="col"` attribute — violates CLAUDE.md rule and WCAG table accessibility.
**Fix:** Add `scope="col"` to all `<th>` in `table_header` macro, settings list, and index page.

### P0-2: Missing `<div id="results-container">` on List Pages
**Files:** `admin/people/list.html`, `admin/settings/list.html`, `admin/notifications/list.html`
**Issue:** CLAUDE.md mandates `<div id="results-container">` on all list pages for HTMX partial swaps. None have it.
**Fix:** Wrap table containers in `<div id="results-container">`.

### P0-3: Sidebar "Dashboard" Link Active-State False Positive
**File:** `admin/components/sidebar.html:15`
**Issue:** `current_path.startswith(href)` with `href="/admin"` matches ALL admin pages. Dashboard is always highlighted.
**Fix:** Use exact match for `/admin` (dashboard), `startswith` for others.

## P1 — High Impact (Visual Polish / Consistency)

### P1-1: Login Page Missing Focus Ring Transition & Loading State
**File:** `admin/login.html`
**Issue:** Input focus rings appear instantly (no transition). No loading indicator on submit. No keyboard-trap prevention.
**Fix:** Add `transition` to focus rings, add loading spinner on form submit.

### P1-2: Form Inputs Missing Focus Transition
**File:** `admin/components/form_macros.html`
**Issue:** All form inputs use `focus:ring-2 focus:ring-primary-500` without `transition` class — focus state snaps abruptly.
**Fix:** Add `transition` or `transition-shadow` to all input classes.

### P1-3: Duplicate `status_badge()` Macros with Different Styles
**Files:** `components/macros.html:3` vs `admin/components/table_macros.html:149`
**Issue:** Two competing `status_badge` implementations with different color maps (emerald vs green, different dark variants). Confusing for maintainers.
**Fix:** Consolidate to a single canonical version in `components/macros.html`.

### P1-4: Topbar Breadcrumb Missing — No Context for Deep Pages
**File:** `admin/components/topbar.html`
**Issue:** Only shows page title. On deep pages (billing/products/edit), user loses navigation context.
**Fix:** Add breadcrumb support via block override pattern.

### P1-5: Empty State Not Used in Settings List
**File:** `admin/settings/list.html:61-69`
**Issue:** Settings empty state is manually built instead of using `empty_state()` macro from table_macros.
**Fix:** Use the existing macro for consistency.

## P2 — Low Priority (Nice to Have)

### P2-1: No Skip-to-Content Link
**File:** `base.html`, `admin/base.html`
**Issue:** No skip-to-content link for keyboard/screen-reader users.

### P2-2: Mobile Sidebar Duplicates Desktop Sidebar Include
**File:** `admin/base.html:36-38`
**Issue:** Sidebar HTML is included twice (desktop + mobile overlay), doubling DOM weight.

### P2-3: Notification Bell Token from Cookie
**File:** `admin/base.html:152-154`
**Issue:** `getToken()` reads raw `access_token` cookie — fragile if cookie name changes.

### P2-4: No Loading/Skeleton States for HTMX Partial Swaps
**Issue:** When HTMX swaps table content, there's no loading indicator beyond the global `htmx-indicator` class.

---

## Wave 1 Implementation Plan (Top 5)

| # | Finding | Impact | Effort |
|---|---------|--------|--------|
| 1 | P0-1: Add `scope="col"` to all `<th>` | Accessibility | Trivial |
| 2 | P0-2: Add `results-container` to list pages | HTMX partial swap | Trivial |
| 3 | P0-3: Fix sidebar active-state for dashboard | Navigation clarity | Trivial |
| 4 | P1-1: Login page focus transitions + loading | First impression | Small |
| 5 | P1-2: Form input focus transitions | Polish | Trivial |
