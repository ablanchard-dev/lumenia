import io, csv, json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from .db import SessionLocal, init_db
from .models import Profile, Journal, KV, Assessment
from .schemas import *
from .llm import decompose, reframe, creative, scenarios, psycho_coach
from .chat import chat_reply
from .entry import get_parcours, get_challenge, verify_challenge, entry_summary
from .assess import entry_score, phq9_score, gad7_score

init_db()
app = FastAPI(title="LumenIa Backend", default_response_class=ORJSONResponse, version="2.2.0")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

@app.get("/healthz")
def healthz():
    return {"ok": True, "version": "2.2.0"}

# ---------------- UI (SPA servie par le backend) ----------------
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")

# ---------------- Portail d'entrée (mini-parcours cognitif) ----------------
@app.get("/entry/parcours")
def entry_parcours(exclude: str = ""):
    seen = {x.strip() for x in exclude.split(",") if x.strip()}
    return get_parcours(seen)

@app.get("/entry/challenge")
def entry_challenge():
    return get_challenge()

@app.post("/entry/verify")
def entry_verify(body: EntryVerifyIn):
    return verify_challenge(body.challenge_id, body.answer)

@app.post("/entry/complete")
def entry_complete(body: EntryCompleteIn):
    results = [r.model_dump() for r in body.results]
    score = sum(1 for r in results if r["ok"] and not r["skipped"])
    summary = json.dumps(entry_summary(results), ensure_ascii=False)
    with SessionLocal() as db:
        db.add(Assessment(kind="entry", payload=json.dumps(results, ensure_ascii=False),
                          score=score, severity=None, risk_flag=False))
        kv = db.get(KV, "profile.entry")
        if not kv:
            db.add(KV(key="profile.entry", value=summary))
        else:
            kv.value = summary
        db.commit()
    return {"ok": True, "score": score, "total": len(results)}

# ---------------- Chat (évaluation interne incluse) ----------------
@app.post("/chat")
def chat(body: ChatIn):
    with SessionLocal() as db:
        prof = db.execute(select(Profile).limit(1)).scalar_one_or_none()
        low_stim = bool(prof and prof.low_stim)
        pacing = prof.pacing if prof else "normal"
        kv = db.get(KV, "profile.entry")
        try:
            entry_profile = json.loads(kv.value) if kv and kv.value else None
        except ValueError:
            entry_profile = None
    out = chat_reply(body.message, [t.model_dump() for t in body.history], low_stim, pacing, entry_profile)
    if out["risk"]:
        with SessionLocal() as db:
            kv = db.get(KV, "risk.flag")
            if not kv:
                db.add(KV(key="risk.flag", value="1"))
            else:
                kv.value = "1"
            db.commit()
    return {"reply": out["reply"], "risk_flag": out["risk"]}

# Consent
@app.get("/consent")
def get_consent():
    with SessionLocal() as db:
        rec = db.get(KV, "consent.accepted")
        return {"accepted": bool(rec and rec.value == "1")}

@app.post("/consent")
def set_consent(accepted: bool):
    with SessionLocal() as db:
        rec = db.get(KV, "consent.accepted")
        if not rec:
            rec = KV(key="consent.accepted", value="1" if accepted else "0")
            db.add(rec)
        else:
            rec.value = "1" if accepted else "0"
        db.commit()
        return {"accepted": accepted}

# Risk flag (read)
@app.get("/risk")
def get_risk():
    with SessionLocal() as db:
        kv = db.get(KV, "risk.flag")
        return {"risk_flag": bool(kv and kv.value == "1")}

# Profile
@app.get("/profile")
def get_profile():
    with SessionLocal() as db:
        prof = db.execute(select(Profile).limit(1)).scalar_one_or_none()
        if not prof:
            prof = Profile()
            db.add(prof); db.commit(); db.refresh(prof)
        return {"id": prof.id, "low_stim": prof.low_stim, "font_size": prof.font_size, "pacing": prof.pacing}

@app.post("/profile")
def set_profile(p: ProfileIn):
    with SessionLocal() as db:
        prof = db.execute(select(Profile).limit(1)).scalar_one_or_none()
        if not prof:
            prof = Profile(); db.add(prof)
        prof.low_stim = p.low_stim
        prof.font_size = p.font_size
        prof.pacing = p.pacing
        db.commit(); db.refresh(prof)
        return {"id": prof.id, "low_stim": prof.low_stim, "font_size": prof.font_size, "pacing": prof.pacing}

@app.post("/adapt")
def adapt(p: ProfileIn):
    tips = []
    if p.low_stim: tips.append("Réduire les animations et le bruit visuel")
    if p.font_size >= 18: tips.append("Activer grande police et interligne augmenté")
    if p.pacing == "slow": tips.append("Mode Pomodoro 10/2")
    return {"ui_tips": tips}

# Focus / impostor / creativity / scenarios
@app.post("/focus/decompose")
def focus_decompose(body: DecomposeIn):
    return {"task": body.task, "steps": decompose(body.task, body.steps)}

@app.post("/impostor/reframe")
def impostor_reframe(body: ReframeIn):
    return {"thought": body.thought, "reframes": reframe(body.thought)}

@app.post("/creativity/generate")
def creativity_generate(body: CreativityIn):
    return {"goal": body.goal, "mode": body.mode, "ideas": creative(body.goal, body.mode)}

@app.post("/scenarios")
def scenarios_generate(body: ScenarioIn):
    return {"context": body.context, "style": body.style, "scripts": scenarios(body.context, body.style)}

# Journal
@app.get("/journal")
def journal_list():
    with SessionLocal() as db:
        rows = db.execute(select(Journal).order_by(Journal.created_at.desc())).scalars().all()
        return [ {"id": j.id, "title": j.title, "content": j.content, "created_at": str(j.created_at)} for j in rows ]

@app.post("/journal")
def journal_add(body: JournalIn):
    with SessionLocal() as db:
        j = Journal(title=body.title, content=body.content)
        db.add(j); db.commit(); db.refresh(j)
        return {"id": j.id, "title": j.title, "content": j.content, "created_at": str(j.created_at)}

@app.get("/journal/export")
def journal_export():
    with SessionLocal() as db:
        rows = db.execute(select(Journal).order_by(Journal.created_at)).scalars().all()
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id","title","content","created_at"])
        for j in rows:
            w.writerow([j.id, j.title, j.content, j.created_at])
        buf.seek(0)
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=journal.csv"})

# Assessments
@app.post("/assessment/entry")
def assess_entry(body: EntryAssessmentIn):
    scores = entry_score(body.answers)
    total = sum(scores.values())
    with SessionLocal() as db:
        db.add(Assessment(kind="entry", payload=json.dumps(body.answers), score=total, severity=None, risk_flag=False))
        db.commit()
    return {"scores": scores, "total": total}

@app.post("/assessment/phq9")
def assess_phq9(body: PHQ9In):
    total, severity, risk = phq9_score(body.items, body.item9)
    with SessionLocal() as db:
        db.add(Assessment(kind="phq9", payload=json.dumps(body.items), score=total, severity=severity, risk_flag=risk))
        kv = db.get(KV, "risk.flag")
        if not kv:
            db.add(KV(key="risk.flag", value="1" if risk else "0"))
        else:
            kv.value = "1" if risk else "0"
        db.commit()
    return {"total": total, "severity": severity, "risk_flag": risk}

@app.post("/assessment/gad7")
def assess_gad7(body: GAD7In):
    total, severity = gad7_score(body.items)
    with SessionLocal() as db:
        db.add(Assessment(kind="gad7", payload=json.dumps(body.items), score=total, severity=severity, risk_flag=False))
        db.commit()
    return {"total": total, "severity": severity}

# Psy coach (gated by risk flag)
@app.post("/psy/coach")
def psy_coach(body: CoachIn):
    with SessionLocal() as db:
        kv = db.get(KV, "risk.flag")
        risky = bool(kv and kv.value == "1")
    if risky:
        return {"blocked": True, "message": "Par prudence, génération limitée. En cas d’urgence: 3114 / 15 / 112."}
    return {"blocked": False, "advice": psycho_coach(body.topic, body.style)}

# Resources
@app.get("/resources")
def resources():
    return {"fr": {"urgence": ["15 (SAMU)", "112 (EU)"], "suicide": ["3114"], "sites": ["https://3114.fr", "https://service-public.fr"]}}

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
