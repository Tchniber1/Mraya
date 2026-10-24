# Mraya — MVP Design (Hack Day, 2026-10-24)

## Goal
Open-source AI style coach. The user uploads a full-body photo and a face photo,
picks a gender theme, and gives age, budget and preferences. Gemma 4 (via the
Gemini API) returns personalised advice and products for clothing, hair, skincare,
perfume, shoes and accessories, including brands and where to buy them. A private
dashboard tracks product status and XP/levels.

Event constraints: built today, public repo, MIT licence, uses Gemma 4 through the
Gemini API (eligible for both "Best Open-Source AI" and "Best Use of Gemma 4").
Feature-complete and bug-free by 17:00.

## Scope (MVP = "A")
- Google sign-in (Firebase Auth, JS SDK) → server verifies ID token → Django session.
- Home: gender choice first (theme switches live), then a form: two photos, age,
  budget + currency, city, style/brand preferences, "suggest brands for me", interests.
- Analysis with Gemma 4 (`gemma-4-31b-it` by default, configurable).
- Dashboard: photos, level ring, XP bar, style score, summary, routine, product list
  with statuses `suggested | started | not_yet | not_interested`.
- XP/levels: profile +50, analysis +100, product started +40, not-interested feedback +5.
  Each product awards each event at most once.
- Persistence: Firestore (primary). A local JSON store is used when Firebase isn't
  configured (dev/tests).
- Remembering the user: 30-day signed-cookie session, theme cookie, Django cache for
  dashboard data, and a localStorage draft of the onboarding form.

## Deferred: "update" packages (B)
Goals/achievements, product replacement re-requests, full settings, analysis history.
These ship later as pip packages exposing the entry-point group `mraya.plugins`
(or listed in `MRAYA_PLUGINS`). Each one is a Django app that is auto-added to
`INSTALLED_APPS` and mounted at `/ext/<label>/`.

## Architecture (one Django app per job)
| app | job |
|---|---|
| `apps.core` | home page, theme resolution, base layout |
| `apps.accounts` | Firebase token verification, session login/logout, `login_required` |
| `apps.storage` | repository interface + `LocalJsonRepository` / `FirestoreRepository` |
| `apps.analysis` | image preparation, prompt, Gemma client, JSON parsing/normalisation |
| `apps.onboarding` | profile/photo form, runs analysis, persists result |
| `apps.progress` | pure XP/level rules |
| `apps.dashboard` | dashboard view, product status API |
| `config.plugins` | discovery of update packages |

Data (document-shaped, the same in both backends):
`users/{uid}` profile + xp + thumbnails · `users/{uid}/analyses/{id}` · `users/{uid}/products/{id}`.

Photos are resized in memory and sent to Gemma. Only small thumbnails (≤320px)
are kept, for the private dashboard.

## Errors
- Invalid or oversized images → form errors.
- Gemma failure or unparseable output → one retry, then a friendly error and the form is kept.
- Bad or expired token → 401 → login page.

## Testing
Django test suite with the local store and a stubbed Gemma client. Covers XP rules,
the parser, storage, auth gating, onboarding → dashboard, and the status API.
`manage.py check_gemma` smoke-tests the real API key.
