<p align="center">
  <img src="static/img/logo.png" alt="Mraya logo" width="120">
</p>

<h1 align="center">Mraya: your open-source AI style mirror</h1>

<p align="center">
  <em>Mraya</em> (مراية) means "mirror" in Moroccan Darija.<br>
  Two photos in, a personal style plan with real, buyable products out, within your budget.
</p>

<p align="center">
  <strong>Built with Gemma 4 · <code>gemma-4-31b-it</code></strong> ·
  Django 5.1 · Firebase · Google Shopping (Serper.dev) · MIT
</p>

Built at **Hacktoberfest Hack Day Rabat × ForgeBots Club UM6P** (24 Oct 2026).

---

## For judges: 60-second overview

| | |
|---|---|
| **Problem** | Style advice is either generic (blogs, influencers) or expensive (personal stylists). Most people can't tell what suits *their* body, face and skin, and AI "recommendations" usually ignore budget and whether you can actually buy the item where you live. |
| **Solution** | Upload a full-body photo and a face photo, then set your budget, country and taste. Mraya returns a plan across clothing, hair, skincare, perfume, shoes and accessories, with **real products, real photos, real store prices and links**, trimmed by code so the total **never exceeds your budget**. |
| **AI** | **Gemma 4 31B IT** (`gemma-4-31b-it`), open-weight and multimodal. It reads both photos plus the profile in one call and returns structured JSON. |
| **What's new vs. "ask a chatbot"** | Gemma's suggestions are grounded in real Google Shopping results for your country, converted to your currency, and checked against the budget. Then they're tracked in a dashboard with XP and levels. |
| **Try it in 2 minutes** | `pip install -r requirements.txt` → `python manage.py seed_demo` → `python manage.py runserver` → click **Try the demo account**. No API keys needed (see [Setup](#setup)). |
| **Tests** | 113 automated tests, about 1.5 s, no keys or network needed: `python manage.py test` |

---
## VIDEO SHOWCASE: https://drive.google.com/file/d/1kdRpWEBIMOqPspYpbo_76WOw9AAYBHJJ/view?usp=sharing

## 1. The problem

- **Advice isn't personal.** "Wear slim fits" means nothing without looking at your body shape, face shape, skin tone and hair.
- **Advice isn't affordable.** Recommendation lists ignore what you can spend. We found this in our own first version: the products Gemma suggested didn't add up to the budget the user gave.
- **Advice isn't buyable where you live.** A product sold only in Paris is useless in Rabat unless you're told so and shown the shipped price.
- **Advice is forgotten.** A chat answer disappears. There's no list to work through and no sense of progress.

## 2. The solution

Mraya is a web app that turns two photos into a plan you can act on:

1. **Sign in** with Google (Firebase Auth), or with the demo account.
2. **Tell Mraya about you:** gender/theme, age, total budget and currency, **shopping country**, city, style taste, favourite brands, and the categories you care about.
3. **Upload two photos:** a full-body photo and a face photo.
4. **Gemma 4 analyses** both photos and writes a summary, a style profile, a style score (0–100), a morning/evening routine, and 2–3 products per category.
5. **Mraya grounds every product** in a real Google Shopping result, searching your country first. Each product gets a photo, store name, price and link.
6. **Mraya enforces the budget in code.** It keeps the most important pick per category, then fills in until the budget is used, and never goes over.
7. **Dashboard:**
   - products grouped by category
   - a separate **"Not sold in your country, available abroad"** section with converted prices and a shipping note
   - a budget bar ("1223.56 of 3000 MAD used")
   - Bought / Not yet / Not for me tracking
   - XP and levels
8. **History, export, settings:**
   - re-open or delete past analyses
   - export the buying list as **CSV** (Excel-ready) or a **printable / PDF** page
   - set your profile picture, country and currency

### Features at a glance

- Gemma 4 multimodal analysis: two images and a profile go in, structured JSON comes out
- Real products: image, store, price and link via Google Shopping (Serper.dev)
- Country-aware search with an abroad fallback (e.g. Morocco → France → USA); 12 countries and 7 currencies
- A hard budget guarantee with per-category allowances
- History with delete (XP you earned is kept), CSV and print export
- Settings page with profile picture (Google photo by default, upload or remove)
- Apple-style "liquid glass" UI with shadcn-style components, three themes (neutral, navy, rose) that blend smoothly, light and phone layouts
- Gamification: +50 XP for the profile, +100 per analysis, +40 per product you start, +5 for feedback
- Privacy by design: photos are resized in memory and only 320 px thumbnails are kept

---

## 3. The role of AI: Gemma 4

**Model:** Gemma 4, 31B parameters, instruction-tuned: `gemma-4-31b-it`. Gemma 4 is Google DeepMind's open-weight model family. We call it through the Gemini API with the `google-genai` SDK, and you can override it with `GEMMA_MODEL` in `.env`.

### What Gemma does

Gemma is the **stylist**. In a **single multimodal call** it receives:

- **Image 1:** the full-body photo, resized to at most 1024 px. Gemma reads body proportions, posture, current outfit and colours from it.
- **Image 2:** the face photo, also at most 1024 px. Gemma reads face shape, skin tone and undertone, visible skin condition and hair from it.
- **The profile:** age, gender, budget and currency, country/city, style taste, brand preferences, chosen categories, and a **budget allowance per category** that the code computes and puts in the prompt.

It returns **one JSON object** containing:
- summary, style profile, style score and routine
- per category: advice and 2–3 products
- per product: name, brand, a `search_query` written for a shop search, `essential`/`nice` priority, estimated price, where to buy, and why it suits the person

Temperature is 0.7.

### What Gemma does *not* do, by design

We don't trust an LLM with facts it can't know, so the code takes over at the boundaries:

| Concern | Who handles it |
|---|---|
| Seeing the person, choosing the style, products and routine | **Gemma 4** |
| Current price, product photo, store and link | **Google Shopping via Serper.dev**, searched with Gemma's `search_query` |
| Currency conversion | Code (`apps/analysis/currency.py`) |
| Staying within budget | Code (`apps/analysis/budget.py`); the prompt asks for it, the code guarantees it |
| Invalid or chatty model output | Parser (`apps/analysis/parser.py`): pulls the JSON out of the reply, normalises the fields, retries once with a stricter instruction |

### Safety rules in the prompt

- Skincare advice is gentle and **non-medical**, and never diagnoses conditions.
- Mraya is respectful and **body-positive**, and never comments negatively on weight.
- Brands you like are preferred; otherwise it picks well-known, reliable brands within the budget.

The full prompt is in [`apps/analysis/prompts.py`](apps/analysis/prompts.py). The pipeline is in [`apps/analysis/service.py`](apps/analysis/service.py).

```
photos + profile ─► Gemma 4 (gemma-4-31b-it) ─► JSON plan
                                                   │
                     parser (validate / normalise) ◄┘
                                │
                     Serper Google Shopping, per product (8 in parallel)
                     your country first ─► abroad fallback ─► search-link fallback
                                │
                     currency conversion ─► fit_to_budget ─► storage ─► dashboard
```

---

## Setup

### Requirements

- Python **3.10+**
- Optional keys, each with a working fallback:

| Key | What it enables | Without it |
|---|---|---|
| `GEMINI_API_KEY` | Real Gemma 4 analyses of your photos | Use `seed_demo` to see a sample plan |
| `SERPER_API_KEY` | Real product photos, prices and links | Gemma's estimated prices and a Google Shopping search link |
| Firebase (5 values + service-account JSON) | Google sign-in and Firestore | Demo account and `data/local_store.json` |

### Install and run

```bash
git clone https://github.com/Tchniber1/Mraya.git
cd Mraya
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
python manage.py runserver
```

Open **http://localhost:8000** and click **Try the demo account**. That button appears when `DJANGO_DEBUG=true` and Firebase isn't configured.

### Demo data without any keys

```bash
python manage.py seed_demo                  # sample plan for the demo account (men theme)
python manage.py seed_demo --gender women   # rose theme
python manage.py seed_demo --live           # also fetch real products (uses ~2 Serper searches)
```

### Gemma 4 (real analyses)

1. Get a free key at https://aistudio.google.com/apikey.
2. In `.env`, set `GEMINI_API_KEY=...`. `GEMMA_MODEL` defaults to `gemma-4-31b-it`.
3. Smoke-test it:
   ```bash
   python manage.py check_gemma          # sends one tiny request
   python manage.py check_gemma --list   # lists the Gemma models your key can use
   ```

### Real products (Serper.dev)

1. Create a key at https://serper.dev (free credits on sign-up).
2. In `.env`, set `SERPER_API_KEY=...`. `SERPER_COUNTRY=ma` is the default country for users who haven't picked one.
3. Each user picks their own shopping country in the form or in **Settings**.

### Firebase (Google sign-in and Firestore)

1. Create a project at https://console.firebase.google.com.
2. **Authentication → Sign-in method →** enable **Google**. `localhost` is an authorised domain by default; `127.0.0.1` is not, so use `localhost`.
3. **Firestore Database →** create the database in production mode.
4. **Project settings → General → Your apps →** add a Web app. Copy `apiKey`, `authDomain`, `projectId` and `appId` into `.env` (`FIREBASE_*`).
5. **Project settings → Service accounts → Generate new private key.** Save the file as `firebase-service-account.json` in the repo root. It is git-ignored; **never commit it**.

**Network blocks `*.firebaseapp.com`?** (The popup closes, or you see "Sign-in was cancelled".)
1. Copy the Web client ID from *Authentication → Sign-in method → Google → Web SDK configuration*.
2. In Google Cloud Console → *APIs & Services → Credentials*, open that client and add `http://localhost` and `http://localhost:8000` to **Authorized JavaScript origins**.
3. Set `GOOGLE_OAUTH_CLIENT_ID=<id>` in `.env` and restart the server.

Recommended Firestore rules. The server uses the Admin SDK, so browsers need no direct access:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} { allow read, write: if false; }
  }
}
```

### All settings (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | `change-me` | Change it for anything public |
| `DJANGO_DEBUG` | `true` | Must be `true` for the demo login |
| `GEMINI_API_KEY` | — | Gemma 4 access |
| `GEMMA_MODEL` | `gemma-4-31b-it` | Model id |
| `SERPER_API_KEY` | — | Google Shopping results |
| `SERPER_COUNTRY` | `ma` | Default shopping country |
| `FIREBASE_*`, `FIREBASE_CREDENTIALS` | — | Sign-in and Firestore |
| `GOOGLE_OAUTH_CLIENT_ID` | — | Alternative Google button |
| `MRAYA_STORAGE` | auto | `firestore` or `local` |
| `MRAYA_DEV_LOGIN` | `true` | Demo login (DEBUG only) |
| `MRAYA_PLUGINS` | — | Extra plugin apps |

---

## Testing

```bash
python manage.py test
```

**113 tests run in about 1.5 s.** They need **no keys and no network**: they use the local JSON store, a fake Gemma client, and canned Serper responses (`apps/analysis/fixtures/serper_shopping.json`). The real Serper key is blanked during tests, so they never spend credits.

| Area | What is covered |
|---|---|
| Gemma output | JSON extraction from fenced or chatty replies, field normalisation, category aliases, retry on invalid JSON |
| Prices and currency | `"MAD 94.09"`, `"€7.49"`, `"1 299,00 MAD"`, `"1.299,00 €"`, `"Free"` → parsed or rejected; conversion between 7 currencies |
| Budget | Allowances add up exactly to the budget; `used ≤ limit` always; essentials first; categories nothing fits show "No pick fits your budget" |
| Shopping | Local-first then abroad; allowance-aware pick; network errors → fallback; `javascript:`/`data:` links rejected |
| Storage | One contract test suite run against **both** backends (local JSON and an in-memory Firestore fake): history, per-analysis products, batch delete |
| Dashboard | Per-analysis view, abroad section, cache invalidation, delete (redirect / 404, never 500), access control by user |
| Export | CSV columns and statuses, UTF-8 for Excel, spreadsheet-formula neutralising, print page |
| Settings | Profile save, avatar upload (crop to square, size and type limits), remove |
| Accounts / UI | Google sign-in keeps your custom name, icons, logo, theme |

### Manual end-to-end check

1. `python manage.py seed_demo --live`, then `runserver`, then **Try the demo account**.
2. The dashboard should show product photos, a budget bar, and an "available abroad" section.
3. Open **Export → CSV** in Excel, and **Export → Print** → Save as PDF.
4. Go to **History** → delete the analysis → you're redirected and the XP stays.
5. Open **Settings** → upload a photo → the avatar in the top bar updates. Switch the theme → the colours blend smoothly.

We also checked the UI with Playwright screenshots in all 3 themes at desktop and phone sizes: no horizontal overflow and no console errors.

---

## Results

What we measured during the hackathon:

- **The budget is now always respected.** In v1, Gemma's picks could exceed the budget. In v2 the code guarantees `used ≤ budget`, and tests pin it.
- **Real products end to end.** In a live demo run (Morocco, 3000 MAD budget):
  - Chanel *Bleu EDT* was found **locally** at Turkish Souq for **900.10 MAD**
  - a Zara Oxford shirt wasn't sold locally, so it was found **abroad** at ZARA France for **≈ 323.46 MAD** (converted from EUR) and shown in the abroad section
  - total: **1223.56 of 3000 MAD**
- **Resilient by design.** If Serper is down, out of credits or unconfigured, every product falls back to Gemma's estimate plus a working search link. Enrichment can't make an analysis fail.
- **Speed.** A full analysis takes about 30–60 s, mostly Gemma's multimodal call. Product searches run 8 in parallel, with a 6 s timeout each.
- **Quality bar:** 113 passing tests, plus a final independent code review. Its Important findings (EU price formats, unsafe links, a stale avatar cache, CSV formula injection) were fixed with regression tests.

## Limitations

We'd rather you hear these from us:

- **AI judgement is subjective.** Gemma's read of body type, skin tone or "style score" can be wrong, and may carry the biases of its training data. Results depend heavily on photo quality and lighting. Mraya is a suggestion tool, not an authority.
- **Not medical advice.** Skincare suggestions are deliberately generic and gentle.
- **Photos go to Google's API** for analysis. We keep only small thumbnails, but users should know their photos leave the server.
- **Exchange rates are fixed** demo rates, not live ones, and abroad prices exclude shipping and customs (the UI says so).
- **Links open Google Shopping's product page**, one click away from the store's own page, because that's what the API returns.
- **Serper credits:** an analysis can use up to 3 searches per product (local, then up to 2 abroad countries).
- **Synchronous analysis:** the request waits for Gemma (up to about 1 minute). A task queue would be the next step for production.
- **Prototype infrastructure:** in-memory cache (single process), the demo login is DEBUG-only, and there's no rate limiting.
- **Known minor gaps:** some currency symbols aren't recognised (₹, CHF, د.م.); Windows shows country flags as letters (MA, FR); tabs are missing a few ARIA attributes.

### What's next

Live exchange rates · a background job queue · virtual try-on previews · Darija/French/Arabic UI · price-drop alerts on "Not yet" items · shareable outfit boards.

---

## Architecture

```
config/             Django project: settings, urls, plugin discovery
apps/
  core/             home page, themes, context processors, {% icon %} tag, test helpers
  accounts/         Firebase ID-token verification → Django session, login_required
  storage/          Repository interface + FirestoreRepository + LocalJsonRepository, seed_demo
  analysis/         images (Pillow) · prompt · Gemma 4 client · parser · shopping · currency · budget · countries
  onboarding/       photo + profile form → runs the analysis → saves it
  progress/         pure XP / level rules
  dashboard/        dashboard, history, delete, CSV/print export, product status API, cache
  settings_page/    profile, country/currency, avatar
templates/          one folder per app + partials (logo)
static/             css (tokens · base · glass · ui components · per page) · js · img
docs/superpowers/   design spec and implementation plan
```

Data layout (the same in Firestore and the local store): `users/{uid}`, `users/{uid}/analyses/{id}`, `users/{uid}/products/{id}`.

### Plugins (update packages)

New features can ship as pip-installable Django apps. Register one with an entry point:

```toml
[project.entry-points."mraya.plugins"]
goals = "mraya_goals"
```

You can also list it in `.env` (`MRAYA_PLUGINS=mraya_goals`). Mraya adds it to `INSTALLED_APPS` and mounts its `urls.py` at `/ext/<name>/`. Plugins can reuse `apps.storage.get_repository()`, `apps.accounts.session.login_required` and `apps.progress.rules`.

---

## Credits

**Team**

| Name | GitHub |
|---|---|
| Taha Chniber | [@Tchniber1](https://github.com/Tchniber1) |
| Mohamed Mahzoul | [@BigCoder-ops](https://github.com/BigCoder-ops) |
| Youssef Afouzar | [@kaneki-hacker](https://github.com/kaneki-hacker) |

**Event:** Hacktoberfest Hack Day Rabat × ForgeBots Club, UM6P (24 Oct 2026)

**AI and services**
- [Gemma 4](https://ai.google.dev/gemma) by Google DeepMind (`gemma-4-31b-it`), via the [Gemini API](https://ai.google.dev/) and the `google-genai` SDK
- [Serper.dev](https://serper.dev): Google Shopping results
- [Firebase](https://firebase.google.com): Authentication and Firestore

**Open source**
- [Django](https://www.djangoproject.com) · [Pillow](https://python-pillow.org) · [python-dotenv](https://github.com/theskumar/python-dotenv) · [firebase-admin](https://github.com/firebase/firebase-admin-python)
- Icons: [Lucide](https://lucide.dev) (ISC). Fonts: [Inter](https://rsms.me/inter/) and [Montserrat](https://fonts.google.com/specimen/Montserrat) (SIL OFL)
- UI inspiration: [shadcn/ui](https://ui.shadcn.com), [Mobbin](https://mobbin.com) and Apple's Liquid Glass design language

**Tools:** developed with the help of Claude Code (Anthropic) as an AI pair programmer.

## Contributing

PRs are welcome, Hacktoberfest included. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © 2026 Taha Chniber, Mohamed Mahzoul, Youssef Afouzar
