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

## Subscription & per-device identity

- **Unique device ID**: a UUID is generated on first launch (`mc_device_id`) and shown under the Subscription tab. All saved data and subscription status are tied to this device/browser.
- **Full-app subscription**: monthly (₹990) and yearly (₹7,990) plans via **Razorpay checkout**. On success the app stores the plan, payment ID and expiry date on the device. A Subscription tab shows status and a device ID, and there is a Demo mode for testing without real payment.
- **Configure your key**: open `payments.js` and replace `razorpayKeyId: 'PASTE_YOUR_RAZORPAY_KEY_ID_HERE'` with your `rzp_live_...` or `rzp_test_...` **key ID** (safe in client code). Set `demoMode: false` to use real checkout. **Never put your Razorpay key secret in this app.**

> ⚠️ **Client-side enforcement caveat:** because this is a static PWA with no backend, subscription status is only browser storage. A determined user can reset it by clearing site data. Real paywall security requires a backend that verifies Razorpay payments via webhooks and serves gated content. Do not rely on this for real revenue protection without that layer.

## Files
| File | Purpose |
|---|---|
| `index.html` | App shell |
| `payments.js` | Device ID, subscription state, Razorpay checkout wrapper |
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
