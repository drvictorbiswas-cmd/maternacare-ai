"""Smoke tests for the Maternacare AI MVP. Run with the Flask server up."""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:5055"
FAIL = []


def req(path, data=None, method=None, expect=200):
    url = BASE + path
    body = None
    headers = {"Content-Type": "application/json"}
    if data is not None:
        body = json.dumps(data).encode()
    r = urllib.request.Request(url, data=body, headers=headers, method=method or ("POST" if data is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            payload = json.loads(resp.read())
            assert resp.status == expect, f"status {resp.status}"
            return payload
    except urllib.error.HTTPError as e:
        assert e.code == expect, f"expected {expect}, got {e.code}: {e.read()[:200]}"
        return json.loads(e.read())


def check(name, cond, detail=""):
    print(("PASS" if cond else "FAIL"), "-", name, detail)
    if not cond:
        FAIL.append(name)


# 1. Strings in all languages
for lang in ("en", "hi", "bn"):
    s = req("/api/strings?lang=" + lang)
    check(f"strings {lang}", len(s) > 60 and s["app_name"] == "Maternacare AI")

# 2. Initial state
st = req("/api/state")
check("initial state no profile", st["profile"] is None)
check("traditions loaded", st["traditions_count"] >= 10)
check("danger signs loaded", st["danger_signs_count"] >= 12)

# 3. Consent enforcement
try:
    req("/api/profile", {"consent": False}, expect=400)
    check("consent enforced", True)
except Exception as e:
    check("consent enforced", False, str(e))

# 4. Profile with LMP -> EDD computed
from datetime import date, timedelta
lmp = (date.today() - timedelta(days=100)).isoformat()
res = req("/api/profile", {
    "consent": True, "language": "hi", "stage": "pregnant", "lmp": lmp,
    "high_risk": False, "conditions": "", "medicines": "", "allergies": "",
    "doctor": "Test Clinic", "emergency_contact": "123", "first_pregnancy": True,
})
check("profile saved", res["ok"])
check("EDD computed = LMP+280", res["profile"]["computed_edd"] == (date.fromisoformat(lmp) + timedelta(days=280)).isoformat())
check("days computed", res["profile"]["days"] == 100)
check("ANC tasks generated", len([t for t in res["tasks"] if t["type"] == "anc_visit"]) >= 8)

# 5. Summary
s = req("/api/summary?lang=en")
check("summary week ~14", s["week"] in (14,), str(s["week"]))
check("summary has edd", s["edd"] is not None)
check("summary next task", s["next"] is not None)

# 6. Triage — emergency bleeding (Hindi + English)
for text in ["heavy bleeding", "बहुत खून", "প্রবল রক্তপাত"]:
    r = req("/api/triage", {"text": text, "language": "en"})
    check(f"triage emergency: {text}", r["alert"] and r["urgency"] == "emergency")

# 7. Triage — newborn honey / jaundice keywords
r = req("/api/triage", {"text": "baby not feeding", "language": "hi"})
check("triage newborn poor feeding", r["alert"] and r["urgency"] == "urgent")

# 8. Triage — benign input should not produce false emergency
r = req("/api/triage", {"text": "what should I eat today", "language": "en"})
check("no false alert on benign text", r["alert"] is False)

# 9. Traditions —蜂蜜/honey contraindicated verdict
trs = req("/api/traditions?lang=en&q=honey")
check("honey practice found", len(trs) >= 1)
if trs:
    check("honey contraindicated", trs[0]["verdict_key"] == "contraindicated", trs[0]["verdict_key"])

# 10. Education stage-appropriate
edu = req("/api/education?lang=hi")
check("education items present", len(edu["items"]) >= 1)
check("education localized", edu["items"][0]["title"] != edu["items"][0].get("title_en", "___"))

# 11. Chat routing — symptom must return danger
c = req("/api/chat", {"text": "severe headache and blurred vision", "language": "en"})
check("chat routes danger first", c["kind"] == "danger")

# 12. Chat routing — tradition
c = req("/api/chat", {"text": "should I take saffron for a fair baby", "language": "en"})
check("chat routes tradition", c["kind"] == "tradition")

# 13. Custom task + toggle + delete
r = req("/api/tasks", {"title": "Blood test", "due": (date.today() + timedelta(days=3)).isoformat(), "type": "custom"})
tid = [t for t in r["tasks"] if t["custom"]][-1]["id"]
r = req(f"/api/tasks/{tid}/done", {})
check("task toggled done", any(t["id"] == tid and t["done"] for t in r["tasks"]))
r = req(f"/api/tasks/{tid}", method="DELETE")
check("task deleted", not any(t["id"] == tid for t in r["tasks"]))

# 14. Feedback + chat history
req("/api/feedback", {"text": "test feedback"})
hist = req("/api/chat")
check("chat history persisted", len(hist) >= 4)

print("\n" + ("ALL PASSED" if not FAIL else f"{len(FAIL)} FAILED: {FAIL}"))
