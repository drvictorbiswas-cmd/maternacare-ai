# Maternacare AI — Installable PWA

**An offline, installable maternal & child-health companion.**

> ⚠️ Prototype disclaimer: health education & navigation only — not a doctor,
> not clinically validated, not for diagnosis or emergencies.

## Live app (installable)

**https://drvictorbiswas-cmd.github.io/maternacare-ai/**

Open on your phone → browser menu → **Add to Home screen** → launches fullscreen
like a native app and works offline.

## What's inside

- **Onboarding + consent** — stage, LMP/EDD/week, risk status, doctor, emergency contact. Stored locally in your browser only.
- **Pregnancy tracker** — computes EDD (LMP + 280 days), trimester, progress.
- **Stage education** — planning, all trimesters, postpartum, newborn, child. Source-tagged.
- **Tradition vs Evidence** — 10 Indian practices with belief, evidence, verdict, alternative, when to see a doctor.
- **Danger-sign triage** — 14 signs across pregnancy/postpartum/newborn, emergency/urgent classification, immediate steps. Safety first; never reassures a serious symptom.
- **Care calendar** — WHO-aligned 8 ANC contacts + Indian immunization schedule, mark-done and custom reminders.
- **Orchestrator chat** — routes safety → schedule → traditions → education; honest fallback.
- **English, हिन्दी, বাংলা** full UI.
- **Offline** — service worker caches everything; all data in localStorage.

## Files

| File | Purpose |
|---|---|
| `index.html` | App shell |
| `engine.js` | Ported clinical rules + i18n (browser JS) |
| `app.js` | UI controller, localStorage |
| `style.css` | Mobile-first styling |
| `sw.js` | Service worker for offline |
| `manifest.json` | PWA install metadata |
| `icon.svg` | App icon |

## Run locally

```bash
cd maternacare-ai
python3 -m http.server 5066
# open http://localhost:5066
```

## Notes

- There is **no backend**. Everything runs in the browser, so the app works offline and needs no server or account.
- Data lives in this browser's localStorage. "Clear data" (⟲ button) wipes it.
- Hosted on GitHub Pages from the `docs/` folder on branch `master` (or root via a workflow — see repo settings).

*Built as a functional Phase 1 MVP — not a static demo.*
