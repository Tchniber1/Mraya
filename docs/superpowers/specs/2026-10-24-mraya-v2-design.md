# Mraya v2 — Design (Hack Day demo, 2026-10-24)

## Intent
Make Mraya demo-ready today: recommendations that respect the budget and show real
product pictures and links, the missing everyday features (history/delete, export,
profile picture), and a clean Apple-style liquid-glass UI with shadcn-quality
components and smooth theme changes.

- **Said by the user:** product pictures; budget must match the products; better
  liquid glass like Apple's; smooth (not sudden) colour transitions; profile picture
  in settings; shadcn / Mobbin-level polish; export the buying list; a link for every
  product; delete a finished analysis; logo comes later.
- **Assumed (agreed in chat):** demo-first scope; Serper.dev for shopping data;
  defaults for export, delete, settings, transitions and logo listed below.
- **Success:** a fresh analysis shows every product with an image, a working link and a
  price, and the total never exceeds the budget; a user can delete an analysis, export
  their list, set an avatar; theme switches blend smoothly; every screen looks tidy in
  all three themes on desktop and phone.
- **Process constraint:** no git commits or pushes. The user runs the app locally first.

## Part 1 — Recommendations

### Flow
`run_analysis` becomes: Gemma → parse → **enrich (Serper)** → **fit budget** → store.

1. **Prompt (`apps/analysis/prompts.py`)**
   - Pass a per-category budget split computed from the total and the chosen
     categories (weights: clothing 35, shoes 20, perfume 15, skincare 12, hair 10,
     accessories 8; re-normalised to the chosen categories).
   - Each product adds `search_query` (brand + exact product + size) and
     `priority` (`essential` | `nice`). Ask for 2–3 products per category.
2. **Parser (`parser.py`)** keeps the new fields (`search_query` falls back to
   `"{brand} {name}"`, `priority` defaults to `nice`).
3. **Shopping (`apps/analysis/shopping.py`, new)**
   - `SERPER_API_KEY` in settings/.env (optional).
   - **Country:** the user picks a country (new `country` field, ISO code, on the home
     form and in Settings; default `ma`). Supported: MA, FR, ES, BE, GB, US, CA, AE,
     SA, DE, IT, NL. Choosing a country pre-selects its currency (MA→MAD, FR/ES/BE/DE/
     IT/NL→EUR, GB→GBP, US→USD, CA→CAD, AE→AED, SA→SAR); the user can still change it.
   - Each product is searched in the user's country first. If nothing usable is found,
     search abroad in order: MA → `fr`, then `us`; every other country → `us`.
     A product found abroad gets `origin: "abroad"` and `origin_country`; local ones
     get `origin: "local"`.
   - `enrich(products, currency, allowances)` runs one `POST https://google.serper.dev/shopping`
     per product in a `ThreadPoolExecutor` (max 8 workers, 6 s timeout each).
     Network via `urllib.request` (no new dependency).
   - Choose the first result with `imageUrl` and `link` whose converted price is
     ≤ the category allowance; otherwise the cheapest result with an image.
   - Fills `image_url`, `link`, `store`, `price`, `currency`, `price_source`
     (`store` | `estimate`), `price_converted` (bool).
   - **Currency:** parse the price string's symbol/code; convert with a fixed table
     in `apps/analysis/currency.py` (MAD, EUR, USD, GBP, CAD, AED, SAR). Unknown currency
     → keep Gemma's estimate.
   - **Fallback** (no key, timeout, no result): keep the estimate, `link` = Google
     Shopping search URL for `search_query`, `image_url` empty (UI shows category icon).
     Enrichment never makes the analysis fail.
4. **Budget (`apps/analysis/budget.py`, new, pure)**
   - `fit_to_budget(products, limit)` → `(kept, summary)`.
   - Pass 1: the cheapest priced product of each category, cheapest categories first,
     while it fits. Pass 2: remaining products ordered by (essential first, price),
     added while they fit. Unpriced products are kept but not counted, and flagged.
   - `summary = {"limit", "used", "currency", "dropped": n}` stored on the analysis as `budget`.

### UI
Product card: image (lazy-loaded, `referrerpolicy="no-referrer"`, category-icon
fallback on error), brand, name, store, price (`≈` when converted or estimated),
**View product ↗** (`target="_blank" rel="noopener noreferrer"`). Budget bar on the
dashboard: "1,840 of 2,000 MAD used".

**Available abroad:** products with `origin: "abroad"` are shown in their own section
below the local categories ("Not sold in <your country> — available abroad"), each card
with the country flag, store, converted price (≈) and the note "Price may not include
shipping or customs." They still count toward the budget.

### Tests
`budget.py` (over budget, one category, missing prices, exact fit); Serper result
selection from a recorded JSON fixture; currency parsing/conversion; no-key fallback;
`run_analysis` with stub Gemma + stub shopping. No network in tests.

## Part 2 — Dashboard features

### Bug fix
The dashboard currently mixes products from every analysis. It now shows only the
products of the analysis being viewed.

### Storage (`apps/storage`)
New `Repository` methods, implemented in `LocalJsonRepository` and `FirestoreRepository`:
- `list_analyses(uid)` → newest first (id, created_at, style_score, budget, product count, thumbs)
- `get_analysis(uid, analysis_id)`
- `delete_analysis(uid, analysis_id)` → removes the analysis and its products (Firestore: one batch). Returns bool.
- `list_products(uid, analysis_id=None)`

Each new analysis stores `body_thumb` / `face_thumb`. Old analyses without them show
the user-level thumbnails.

### History & delete
- `/dashboard/` → latest analysis; `/dashboard/<id>/` → a specific one.
- `/dashboard/history/` → cards (thumbs, date, score, budget used/limit).
- `POST /dashboard/<id>/delete/` behind a confirm dialog. Clears the dashboard cache.
  XP already earned is kept. No analyses left → redirect to home and set
  `has_analysis = False`.

### Export (`apps/dashboard/export.py`)
- `/dashboard/<id>/export.csv` — UTF-8 with BOM; columns: category, brand, name,
  price, currency, store, link, status. Includes `started` and `not_yet` (and
  `suggested`, as "to decide"); excludes `not_interested`.
- `/dashboard/<id>/export/print/` — standalone white page with images, links, total
  and the logo; `window.print()` button. Both views only serve the signed-in user's data.

### Settings (`apps/settings_page`, new app)
- `/settings/`: avatar (Google `picture` saved at sign-in as `google_picture`; upload →
  Pillow centre-crop to a 256 px square JPEG data URI in `avatar`; Remove → back to
  Google photo, then initials), display name, gender theme, country, default currency.
- Header avatar opens a dropdown: Dashboard, History, Settings, Sign out.

### Tests
Delete in both backends (Firestore with a fake client); dashboard filtering by
analysis; CSV contents and access control (404 for another user's id); avatar
upload/crop/remove; settings form validation; auth gating on all new URLs.

## Part 3 — Visual redesign

### Principles
- **Glass only on the controls layer** (top bar, dropdowns, dialogs, floating action
  bar, toasts). Content uses calm, near-opaque cards.
- Glass recipe: strong blur + saturation, bright top rim (inset highlight +
  gradient-masked border), faint inner glow, soft lift shadow, hover/press response.
  Chromium-only SVG displacement on edges as optional progressive enhancement.
- 4/8 px spacing scale; one type scale; Montserrat for headings/brand, Inter for body
  and numbers; WCAG AA contrast in all themes; Lucide inline-SVG icons replace emoji;
  one primary action per screen; designed empty and loading states.

### Components (`static/css/ui.css`, `static/js/ui.js`)
shadcn-style Button (default/secondary/outline/ghost/destructive), Card, Badge,
Avatar, Dropdown Menu, Dialog, Tabs, Progress, Skeleton, Separator, Toast (Sonner
style), Tooltip. JS handles dialogs, menus and tabs with keyboard support and focus trap.

### Screens
- **Dashboard:** summary row (style score, budget bar, level ring) → category Tabs →
  product-card grid; Export dropdown and History in the header.
- **Analysis loading:** stepped loader (Reading photos → Building your plan → Finding
  real products → Fitting your budget) with skeletons.
- **Login / Home / History / Settings / Print:** same system; logo slot.

### Theme transition
All theme colour tokens registered with `@property` (`syntax: '<color>'`) and
transitioned on `body` over ~0.8 s, so background, blobs, accents and text blend.
Blobs drift slowly. Everything respects `prefers-reduced-motion`.

### Logo
`templates/partials/logo.html` renders a wordmark placeholder; replacing it with the
user's file is a one-line change (`static/img/logo.svg`).

### Verification
Template render tests; then run the app and screenshot every screen in the three
themes at desktop and phone width before claiming done.

### Cut first if short on time
Chromium edge displacement, drifting blobs.

## Out of scope
React/shadcn packages (styles are re-created in plain CSS), live currency rates,
image proxying/caching, Mobbin screen copying (needs login; user may send screenshots).
