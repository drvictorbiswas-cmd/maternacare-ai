"""Maternacare AI — Flask app.

Phase 1 MVP: onboarding + consent, stage/week tracking, education, traditional
practice evaluator, danger-sign triage, care calendar with reminders, and a
rule-based orchestrator chat. Data saved in SQLite on this device.

IMPORTANT: This is a prototype. No external AI API, no clinical validation, no
regulator approval. It must not be used for diagnosis or emergencies.
"""

import json
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request

from engine import clinical_rules as cr
from engine.i18n import STRINGS, t

app = Flask(__name__)
BASE = Path(__file__).parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", str(BASE / "data" / "maternacare.db")))


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                due TEXT NOT NULL,
                week INTEGER,
                note TEXT,
                custom INTEGER NOT NULL DEFAULT 0,
                done INTEGER NOT NULL DEFAULT 0,
                done_at TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                kind TEXT,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL
            )
        """)
        db.commit()


init_db()


def log_action(action, detail=""):
    db = get_db()
    db.execute("INSERT INTO audit(action, detail, created_at) VALUES (?,?,?)",
               (action, detail, datetime.now().isoformat()))
    db.commit()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/strings")
def strings():
    lang = request.args.get("lang", "en")
    return jsonify(STRINGS.get(lang, STRINGS["en"]))


@app.route("/api/state")
def state():
    db = get_db()
    row = db.execute("SELECT data FROM profiles WHERE id=1").fetchone()
    profile = json.loads(row["data"]) if row else None
    return jsonify({
        "profile": profile,
        "languages": list(STRINGS.keys()),
        "traditions_count": len(cr.TRADITIONS),
        "danger_signs_count": len(cr.DANGER_SIGNS),
    })


@app.route("/api/profile", methods=["POST"])
def save_profile():
    data = request.get_json(force=True) or {}
    if not data.get("consent"):
        return jsonify({"error": t(data.get("language", "en"), "missing_consent")}), 400

    # EDD calculation — never invented; derived from LMP/EDD/weeks.
    edd, days = cr.compute_edd(
        data.get("lmp") or None,
        data.get("edd") or None,
        data.get("weeks") or None,
    )
    data["computed_edd"] = edd.isoformat() if edd else None
    data["days"] = days
    stage = data.get("stage", "pregnancy")
    data["stage"] = "pregnancy" if stage == "pregnant" else stage

    db = get_db()
    db.execute(
        "INSERT INTO profiles(id, data, updated_at) VALUES (1,?,?) "
        "ON CONFLICT(id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
        (json.dumps(data), datetime.now().isoformat()),
    )

    # Generate guidance tasks only for pregnancy stage, once.
    if data["stage"] == "pregnancy" and edd:
        existing = db.execute("SELECT COUNT(*) c FROM tasks WHERE custom=0").fetchone()["c"]
        if existing == 0:
            for item in cr.anc_schedule(edd.isoformat(), data.get("high_risk") in (True, "yes", "true", "on")):
                db.execute(
                    "INSERT INTO tasks(id,type,title,due,week,note) VALUES (?,?,?,?,?,?)",
                    (item["id"], item["type"], json.dumps({
                        "en": item["title_en"], "hi": item["title_hi"], "bn": item["title_bn"]
                    }), item["due"], item.get("week"), json.dumps({
                        "en": item["note_en"], "hi": item["note_hi"], "bn": item["note_bn"]
                    })),
                )
    db.commit()
    log_action("profile_saved", f"stage={data['stage']}")
    return jsonify({"ok": True, "profile": data, "tasks": get_tasks()})


@app.route("/api/profile", methods=["DELETE"])
def clear_profile():
    db = get_db()
    for table in ("profiles", "tasks", "chat", "feedback", "audit"):
        db.execute(f"DELETE FROM {table}")
    db.commit()
    return jsonify({"ok": True})


def task_to_dict(row):
    title = json.loads(row["title"]) if row["title"].startswith("{") else {"en": row["title"], "hi": row["title"], "bn": row["title"]}
    note = None
    if row["note"]:
        note = json.loads(row["note"]) if row["note"].startswith("{") else {"en": row["note"], "hi": row["note"], "bn": row["note"]}
    due = date.fromisoformat(row["due"])
    today = date.today()
    return {
        "id": row["id"], "type": row["type"], "title": title, "note": note,
        "due": row["due"], "week": row["week"], "done": bool(row["done"]),
        "custom": bool(row["custom"]),
        "status": "done" if row["done"] else ("overdue" if due < today else "upcoming"),
        "days": (due - today).days,
    }


def get_tasks():
    rows = get_db().execute("SELECT * FROM tasks ORDER BY due").fetchall()
    return [task_to_dict(r) for r in rows]


@app.route("/api/tasks")
def tasks():
    return jsonify(get_tasks())


@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.get_json(force=True) or {}
    name = (data.get("title") or "").strip()
    due = (data.get("due") or "").strip()
    if not name or not due:
        return jsonify({"error": "title and due required"}), 400
    tid = "custom_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
    db = get_db()
    db.execute(
        "INSERT INTO tasks(id,type,title,due,custom) VALUES (?,?,?,?,1)",
        (tid, data.get("type", "custom"), json.dumps({"en": name, "hi": name, "bn": name}), due),
    )
    db.commit()
    log_action("task_added", tid)
    return jsonify({"ok": True, "tasks": get_tasks()})


@app.route("/api/tasks/<tid>/done", methods=["POST"])
def toggle_task(tid):
    db = get_db()
    row = db.execute("SELECT done FROM tasks WHERE id=?", (tid,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    new = 0 if row["done"] else 1
    db.execute("UPDATE tasks SET done=?, done_at=? WHERE id=?",
               (new, datetime.now().isoformat() if new else None, tid))
    db.commit()
    log_action("task_toggled", f"{tid}={new}")
    return jsonify({"ok": True, "tasks": get_tasks()})


@app.route("/api/tasks/<tid>", methods=["DELETE"])
def delete_task(tid):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.commit()
    return jsonify({"ok": True, "tasks": get_tasks()})


@app.route("/api/education")
def education():
    db = get_db()
    row = db.execute("SELECT data FROM profiles WHERE id=1").fetchone()
    profile = json.loads(row["data"]) if row else {}
    content = cr.education_for(profile.get("stage", "pregnancy"), profile.get("days"))
    lang = request.args.get("lang", "en")
    out = []
    for item in content:
        out.append({
            "title": item.get(f"title_{lang}", item["title_en"]),
            "body": item.get(f"body_{lang}", item["body_en"]),
            "source": item["source"],
        })
    return jsonify({"stage": profile.get("stage"), "week": (profile.get("days") or 0) // 7, "items": out})


@app.route("/api/traditions")
def traditions():
    lang = request.args.get("lang", "en")
    q = (request.args.get("q") or "").lower()
    out = []
    for tr in cr.TRADITIONS:
        haystack = " ".join([
            tr["name"], tr.get("name_hi", ""), tr.get("name_bn", ""),
            tr["belief_en"], tr["belief_hi"], tr["belief_bn"],
        ]).lower()
        if q and q not in haystack:
            continue
        vlabel = cr.VERDICT_LABELS.get(tr["verdict"], ("Unknown",) * 3)
        vi = {"en": 0, "hi": 1, "bn": 2}.get(lang, 0)
        out.append({
            "name": tr.get(f"name_{lang}", tr["name"]),
            "belief": tr.get(f"belief_{lang}", tr["belief_en"]),
            "why": tr.get(f"why_{lang}", tr["why_en"]),
            "evidence": tr.get(f"evidence_{lang}", tr["evidence_en"]),
            "benefit": tr.get(f"benefit_{lang}", tr["benefit_en"]),
            "risk": tr["risk_en"],
            "verdict": vlabel[vi],
            "verdict_key": tr["verdict"],
            "alternative": tr.get(f"alternative_{lang}", tr["alternative_en"]),
            "doctor": tr.get(f"doctor_{lang}", tr["doctor_en"]),
            "source": tr["source"],
        })
    return jsonify(out)


@app.route("/api/triage", methods=["POST"])
def triage():
    data = request.get_json(force=True) or {}
    lang = data.get("language", "en")
    db = get_db()
    row = db.execute("SELECT data FROM profiles WHERE id=1").fetchone()
    profile = json.loads(row["data"]) if row else {}
    stage = profile.get("stage", "pregnancy")
    triage_stage = {"pregnancy": "pregnancy", "postpartum": "postpartum,newborn"}.get(stage, "newborn,child")
    result = cr.triage_symptoms(data.get("text", ""), triage_stage)
    log_action("triage", f"stage={stage} result={result['id'] if result else 'none'}")
    if not result:
        return jsonify({"alert": False, "message": t(lang, "no_answer")})
    return jsonify({
        "alert": True,
        "urgency": result["urgency"],
        "reason": result.get(f"reason_{lang}", result["reason_en"]),
        "action": result.get(f"action_{lang}", result["action_en"]),
        "steps": result["steps_en"],
        "also": result["also"],
        "emergency_line": t(lang, "call102"),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    lang = data.get("language", "en")
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400

    db = get_db()
    prow = db.execute("SELECT data FROM profiles WHERE id=1").fetchone()
    profile = json.loads(prow["data"]) if prow else {"stage": "pregnancy"}
    tasks = get_tasks()

    reply = cr.chat_reply(text, lang, profile, tasks)
    shown = reply.get(f"text_{lang}", reply.get("text_en", ""))
    db.execute("INSERT INTO chat(role,text,kind,created_at) VALUES (?,?,?,?)",
               ("user", text, None, datetime.now().isoformat()))
    db.execute("INSERT INTO chat(role,text,kind,created_at) VALUES (?,?,?,?)",
               ("assistant", shown, reply["kind"], datetime.now().isoformat()))
    db.commit()
    log_action("chat", reply["kind"])
    return jsonify({"reply": shown, "kind": reply["kind"], "alert": reply.get("alert")})


@app.route("/api/chat", methods=["GET"])
def chat_history():
    rows = get_db().execute("SELECT role,text,kind FROM chat ORDER BY id DESC LIMIT 40").fetchall()
    return jsonify([dict(r) for r in rows][::-1])


@app.route("/api/chat", methods=["DELETE"])
def clear_chat():
    get_db().execute("DELETE FROM chat")
    get_db().commit()
    return jsonify({"ok": True})


@app.route("/api/feedback", methods=["POST"])
def feedback():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400
    db = get_db()
    db.execute("INSERT INTO feedback(text,created_at) VALUES (?,?)",
               (text, datetime.now().isoformat()))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/summary")
def summary():
    db = get_db()
    prow = db.execute("SELECT data FROM profiles WHERE id=1").fetchone()
    profile = json.loads(prow["data"]) if prow else {}
    tasks = get_tasks()
    lang = request.args.get("lang", "en")
    edd = profile.get("computed_edd")
    days = profile.get("days")
    week = (days or 0) // 7
    stage = profile.get("stage", "pregnancy")
    if stage == "pregnancy":
        key = cr.stage_from_days(days)
    else:
        key = stage
    tri = cr.trimester_key(key)
    open_tasks = [x for x in tasks if not x["done"]]
    nxt = sorted(open_tasks, key=lambda x: x["due"])
    return jsonify({
        "stage": stage,
        "week": week,
        "trimester": {"en": STRINGS["en"].get(tri, ""), "hi": STRINGS["hi"].get(tri, ""), "bn": STRINGS["bn"].get(tri, "")},
        "edd": edd,
        "days_left": (date.fromisoformat(edd) - date.today()).days if edd else None,
        "next": nxt[0] if nxt else None,
        "open_count": len(open_tasks),
        "done_count": len(tasks) - len(open_tasks),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5055)), debug=os.environ.get("FLASK_DEBUG", "1") == "1")
