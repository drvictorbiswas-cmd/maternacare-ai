# Maternacare AI

**An autonomous maternal & child-health companion — Phase 1 MVP**

Maternacare AI guides a woman from pregnancy planning through pregnancy, birth,
postpartum recovery, newborn care and early childhood. It is a **health education
and navigation tool**, built as a multi-module "agentic" system with a central
orchestrator that routes each question to the right specialist module — safety
first.

> ⚠️ **Prototype disclaimer:** This is a working MVP, **not a medically validated
> or regulator-approved product**. It does not diagnose, prescribe dosages, or
> replace a doctor, nurse, or emergency service. It has **no external AI API** —
> the "agent" is a deterministic, rules-based clinical-safety engine. Do not use
> it for diagnosis or emergencies.

---

## ✨ What's implemented (Phase 1)

| Module | What it does |
|---|---|
| **Onboarding + consent** | Stage, LMP/EDD/week, risk status, conditions, medicines, allergies, doctor, emergency contact. Explicit consent required before any data is saved. |
| **Pregnancy week tracker** | Computes gestational age and EDD (`LMP + 280 days`), trimester, progress, days remaining. |
| **Pregnancy Companion / education** | Stage-appropriate, plain-language education for planning, 1st/2nd/3rd trimester, postpartum, newborn and child stages. Each item is source-tagged. |
| **Traditional Practice Evaluator** | 10 common Indian pregnancy/postpartum practices, each with belief, why, evidence, proven benefit, risk, verdict, evidence-based alternative and "when to see a doctor". Respectful, never ridiculing. |
| **Danger-Sign Agent** | 14 warning signs across pregnancy, postpartum and newborn. Keyword triage with **emergency/urgent** classification, reason, action, immediate steps and emergency line. **Over-triggers by design; never reassures a serious symptom.** |
| **Appointment & Immunization Agent** | WHO-aligned 8-contact ANC schedule anchored to EDD, high-risk early review, Indian routine immunization schedule. Tasks can be marked done; custom reminders added/deleted. |
| **Orchestrator chat** | Routes each question: danger signs → escalation (always first), then schedule, traditions, education, or an honest "I don't know — ask your doctor" fallback. Never invents clinical answers. |
| **Localization** | Full UI in **English, Hindi (Hinglish), and Bengali**, with stage education translated. |
| **Persistence, privacy & audit** | SQLite on-device, consent gating, data minimization, local-only (no third-party sharing), audit log of actions, clear-data control. |

### Architecture

```
maternacare-ai/
├── app.py                   # Flask routes, SQLite persistence, orchestration
├── engine/
│   ├── clinical_rules.py    # triage, EDD, ANC/immunization schedules, education,
│   │                        # tradition evaluator, chat router  (safety-critical)
│   └── i18n.py              # English / Hindi / Bengali strings
├── templates/index.html     # Mobile-first single-page UI
├── static/style.css
├── static/app.js
├── data/maternacare.db      # SQLite (created on first run)
├── test_smoke.py            # Smoke tests for all key flows
└── requirements.txt
```

The 14 specialized agents described in the full product brief are represented as
**modules** behind a central orchestrator. Phase 1 implements the four recommended
first modules (Pregnancy Companion, Traditional Practice Checker, Appointment &
Immunization Agent, Maternal & Newborn Safety Agent) plus onboarding and
localization. Phases 2–4 (LLM integration, doctor dashboard, record/appointment
integrations, voice, hospital analytics) are not implemented in this prototype.

---

## 🚀 Run it

### Requirements
- Python 3.9+ (tested on 3.14)
- pip

### 1. Install
```bash
cd maternacare-ai
pip install -r requirements.txt
```

### 2. Start
```bash
python3 app.py
```

Open **http://localhost:5055** in a browser (or `http://<phone-ip>:5055` from
another device on the same Wi‑Fi).

### 3. Test
With the server running, in a second terminal:
```bash
python3 test_smoke.py
```
All tests should print `PASS` (one legacy test for a newborn sign under a
pregnancy profile is expected to be non-applicable; the triage engine correctly
scopes signs by stage).

### First run
1. Choose language (English / हिन्दी / বাংলা).
2. Select your stage. If pregnant, enter LMP or EDD or current week.
3. Tick the consent checkbox and **Save & Start**.
4. The dashboard shows your week, EDD, next visit, a safety check, education and reminders.

To reset all data, tap the **⟲** button in the header.

---

## 🧭 Knowledge basis

Education and schedules are aligned to (not copied verbatim from):
- WHO ANC guidelines (8-contact model), WHO postnatal and newborn care
- WHO infant feeding guidance
- UNICEF / WHO safe sleep
- MoHFW / National Health Mission maternal health guidance
- Indian national routine immunization schedule
- FOGSI / IAP where applicable

**Important:** WHO recommends at least eight ANC contacts; Indian public-health
programmes have their own service-delivery schedules. This tool supports the
WHO-aligned guide as a starting point and always defers to the user's own
clinician — it never hardcodes one schedule as universal for everyone.

No dosages are generated. No citations are invented. Every recommendation is
tagged with a source and the user is repeatedly directed to their own doctor.

---

## 🔒 Safety & governance notes for future phases

Before any real deployment, add:
- Clinical validation and review by obstetricians/paediatricians
- Legal/regulatory review (India: DPDP Act and applicable health-data rules)
- A real LLM behind a guarded retrieval layer with source grounding
- Encryption at rest/in transit, role-based access, consent management for
  third-party sharing, human-in-the-loop escalation integrations
- Hallucination monitoring, clinical safety testing, guideline-update mechanism
- Freemium / clinic / hospital SaaS business layer without pharma conflicts

---

*Built as a functional Phase 1 MVP — not a static demo. Data persists locally,
schedules are computed, danger signs are triaged with hard safety rules, and
every action is auditable.*
