# Mraya — your open-source AI style mirror

> *Mraya* (مراية) means "mirror" in Moroccan Darija.

Mraya is an open-source AI style coach built on **Gemma 4** (an open-weight model, served through the Gemini API).
Upload a **full-body photo** and a **face photo**, and give your age, budget and taste. Mraya then builds a personal plan for:

**clothing · hair products · skincare routine · perfume · shoes · accessories**

The plan comes with real products, brands (your favourites, or ones Mraya suggests), prices that fit your budget, and where to buy them.
A private dashboard tracks what you bought, what you'll try later and what isn't for you. A **level & XP system** rewards your style progress.

Built at **Hacktoberfest Hack Day Rabat × ForgeBots Club UM6P** (24 Oct 2026).

## Features

- **Google sign-in** with Firebase Auth; your data is stored in **Firestore**
- **Adaptive liquid-glass UI** in Montserrat: neutral palette at first, then a navy theme (men) or a rose & ice theme (women)
- **Gemma 4 multimodal analysis** of both photos plus your profile → summary, style profile, style score, daily routine and products
- **Product tracker**: Bought / Not yet / Not for me
- **XP & levels**: +50 for completing your profile, +100 per analysis, +40 per product you start, +5 for feedback
- **Remembers you**: 30-day session cookie, theme cookie, server cache, and a form draft saved in your browser
- **Modular Django apps**, one per job, so bugs stay contained
- **Update packages**: new features plug in as pip-installable Django apps (see [Plugins](#plugins-update-packages))

## Quick start

```bash
git clone https://github.com/Tchniber1/Mraya.git
cd Mraya
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then fill in GEMINI_API_KEY (and Firebase, optional)
python manage.py check_gemma   # smoke-test your Gemma 4 key
python manage.py runserver
```

Open http://127.0.0.1:8000.

- **Without Firebase:** a *"Try the demo account"* button appears (only when `DJANGO_DEBUG=true`), and data is saved to `data/local_store.json`.
- **Offline demo:** `python manage.py seed_demo --gender women` fills the demo account with a sample plan.

### Gemma 4 setup

1. Get a free key at https://aistudio.google.com/apikey.
2. Set `GEMINI_API_KEY`. `GEMMA_MODEL` defaults to `gemma-4-31b-it`. Run `python manage.py check_gemma --list` to see the Gemma models your key can use.

### Firebase setup (Google login + Firestore)

1. Create a project at https://console.firebase.google.com.
2. **Authentication → Sign-in method →** enable **Google**. Add `localhost` to the authorised domains.
3. **Firestore Database →** create the database (production mode).
4. **Project settings → General → Your apps →** add a Web app. Copy `apiKey`, `authDomain`, `projectId` and `appId` into `.env`.
5. **Project settings → Service accounts → Generate new private key.** Save the file as `firebase-service-account.json` in the repo root. It is git-ignored; never commit it.

Recommended Firestore rules (the server uses the Admin SDK, so clients don't need direct access):

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} { allow read, write: if false; }
  }
}
```

## Architecture

```
config/            Django project: settings, urls, plugin discovery
apps/
  core/            home page, theme resolution (neutral / men / women), test helpers
  accounts/        Firebase ID-token verification → Django session, login_required
  storage/         Repository interface + FirestoreRepository + LocalJsonRepository
  analysis/        image prep (Pillow), prompt, Gemma 4 client, JSON parser
  onboarding/      the photo + profile form → runs the analysis → saves it
  progress/        pure XP / level rules
  dashboard/       dashboard view, product status API, cache
templates/         one folder per app
static/css/        tokens (palettes) · base · glass · one file per page
static/js/         common · auth · onboarding · dashboard
docs/              design spec
```

Request flow: **login** → `accounts` stores the Firebase uid in a signed session cookie → **home** (`core`) → **analyze** (`onboarding` → `analysis` → Gemma 4) → `storage` → **dashboard** (`dashboard` + `progress`).

Data layout (the same in Firestore and the local store):
`users/{uid}`, `users/{uid}/analyses/{id}`, `users/{uid}/products/{id}`.

Privacy: photos are resized in memory and sent to Gemma. Only 320px thumbnails are kept, for your private dashboard.

## Plugins (update packages)

Features after the MVP ship as separate pip packages, so the core stays small and stable. Planned: goals & achievements, product replacement requests, a settings tab, and analysis history.

A plugin is a normal Django app. To register it, add an entry point:

```toml
# pyproject.toml of the plugin
[project.entry-points."mraya.plugins"]
goals = "mraya_goals"
```

You can also list it in `.env`: `MRAYA_PLUGINS=mraya_goals`. Mraya adds the plugin to `INSTALLED_APPS` and mounts its `urls.py` at `/ext/<name>/`.
A plugin can reuse `apps.storage.get_repository()`, `apps.accounts.session.login_required` and `apps.progress.rules`.

## Tests

```bash
python manage.py test apps
```

Tests use the local JSON store and a fake Gemma client, so they need no keys or network.

## Contributing

PRs are welcome, Hacktoberfest included. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © 2026 Taha Chniber
