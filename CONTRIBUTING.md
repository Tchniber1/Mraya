# Contributing to Mraya

Thanks for helping! Mraya takes part in **Hacktoberfest**. Quality PRs count, spam PRs get the `spam` label.

## Getting started

1. Fork the repo and create a branch: `git checkout -b feat/short-description`.
2. Follow the [Quick start](README.md#quick-start). You don't need Firebase: use the demo account.
3. Run the tests before you push: `python manage.py test apps`.

## Where things go

Each Django app has **one job** (see the README architecture section). Put your change in the app that owns it:

| You are changing… | Look in |
|---|---|
| Prompt, model call, parsing Gemma's answer | `apps/analysis/` |
| XP amounts, levels, titles | `apps/progress/rules.py` |
| Saving or reading data | `apps/storage/` (update **both** backends) |
| Login, sessions | `apps/accounts/` |
| The onboarding form | `apps/onboarding/` + `templates/core/home.html` |
| The dashboard | `apps/dashboard/` + `templates/dashboard/` |
| Colours, glass effect | `static/css/tokens.css`, `static/css/glass.css` |

Big new features should be **plugins** (see [Plugins](README.md#plugins-update-packages)).

## Pull requests

- Keep each PR focused on one fix or feature.
- Add or update tests in the app's `tests.py`.
- Match the existing style: small functions, docstrings on modules, no unused code.
- Never commit secrets (`.env`, service-account JSON).
- Describe what changed and how you tested it. Add a screenshot for UI changes.

## Good first issues

- Translations (French, Arabic, Darija)
- Accessibility improvements
- More currencies and local stores
- New plugins: goals, product replacement, history, settings

## Code of conduct

Be kind, be constructive, and respect everyone's body, style and budget, just as Mraya does.
