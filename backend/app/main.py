import io, csv, json
from pathlib import Path
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse, StreamingResponse, FileResponse
import mimetypes

from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from .db import SessionLocal, init_db
from .models import Profile, Journal, KV, Assessment
from .schemas import *
from .llm import decompose, reframe, creative, scenarios, psycho_coach
from .chat import chat_reply, detect_crisis, SAFETY_REPLY
from .entry import (get_parcours, get_challenge, verify_challenge, entry_summary,
                    entry_passed, entry_is_complete, entry_is_gradable, _BY_ID)
from .assess import entry_score, phq9_score, gad7_score

init_db()

# 18/09/2026 : ce numero etait ecrit DEUX fois a la main -- ici et dans /healthz.
# Les deux disaient la meme chose, et rien ne les tenait ensemble. Un superviseur
# lit /healthz pour savoir quelle version tourne, un client lit le schema pour
# savoir a quoi il parle : deux reponses, c'est un deploiement qu'on croit fait.
VERSION = "2.3.0"

app = FastAPI(title="LumenIa Backend", default_response_class=ORJSONResponse, version=VERSION)

# Le premier chargement de l'accueil pesait 71,4 Ko de texte brut alors que tout
# navigateur annonce `Accept-Encoding: gzip` ; compressé, il en pèse 20,4 (mesuré
# le 18/09/2026). Sur un lien lent, ces 51 Ko sont des secondes d'écran blanc pour
# quelqu'un qui cherche le 3114.
#
# Compresser une réponse chiffrée n'est sûr que si elle ne transporte aucun secret
# (attaque BREACH). Lumenia n'en met aucun : ni cookie de session, ni jeton CSRF.
# C'est une condition, pas un acquis — `test_ce_qui_part_sur_le_reseau_est_compresse`
# la vérifie sur les sources et rougit le jour où un secret apparaît.
#
# 500 octets : en dessous, l'en-tête de gzip coûte plus que ce qu'il fait gagner.
app.add_middleware(GZipMiddleware, minimum_size=500)


# ---------------- Refuser une saisie sans la répéter ----------------
# 18/09/2026. Par défaut, le 422 de FastAPI recopie la valeur refusée dans
# `detail[].input`. Sur Lumenia, cette valeur c'est ce que quelqu'un vient
# d'écrire de lui — et un corps d'erreur est justement ce qu'un proxy, un
# journal d'accès ou un rapport de plantage côté navigateur conserve.
#
# On garde ce qui sert à corriger la saisie (quel champ, pourquoi) et on jette
# ce qui n'apprend rien à personne d'autre qu'à celui qui l'a déjà écrit.
@app.exception_handler(RequestValidationError)
def _refus_sans_echo(request, exc: RequestValidationError):
    fautes = [
        {"type": f.get("type", ""), "loc": f.get("loc", ()), "msg": f.get("msg", "")}
        for f in exc.errors()
    ]
    return ORJSONResponse(status_code=422, content={"detail": fautes})


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

@app.get("/healthz")
def healthz():
    return {"ok": True, "version": VERSION}

# ---------------- UI (SPA servie par le backend) ----------------
@app.get("/", include_in_schema=False)
def index():
    # Passe par web.page : l'origine publique est injectee dans canonical et og:image.
    from . import web
    return web.page(STATIC_DIR, "index.html")

# ---------------- Portail d'entrée (mini-parcours cognitif) ----------------
@app.get("/entry/parcours")
def entry_parcours(exclude: str = ""):
    # Tirer un parcours, c'est COMMENCER une tentative : ce que le serveur a constaté
    # dans la précédente ne la concerne plus.
    #
    # 17/09/2026 — sans cette ligne, un « ok » survivait à une tentative abandonnée
    # (la règle « une bonne réponse reste bonne » n'expirait jamais), et une épreuve
    # ratée dans la tentative suivante comptait quand même comme juste. Le seuil
    # d'entrée s'ouvrait alors en partie sur une tentative précédente — pour une garde,
    # c'est une porte entrebâillée, pas un détail de score.
    _VERIFIED.clear()
    seen = {x.strip() for x in exclude.split(",") if x.strip()}
    return get_parcours(seen)

@app.get("/entry/challenge")
def entry_challenge():
    return get_challenge()

# Ce que le SERVEUR a constaté à /entry/verify, par épreuve : "ok", "undetermined" ou "ko".
# /entry/complete ne compte que ça : le `ok` envoyé par le client ouvrait le chat à
# 30 résultats inventés (vérifié le 16/09). Une bonne réponse obtenue après un essai
# raté reste bonne (le front autorise les nouvelles tentatives avec indice).
# ponytail: mémoire du process, mono-utilisateur local comme le gate lui-même ; un
# redémarrage en plein parcours fait échouer fermé (épreuves non vérifiées).
_VERIFIED: dict[str, str] = {}

@app.post("/entry/verify")
def entry_verify(body: EntryVerifyIn):
    # 18/09/2026 — la detresse d'abord, l'epreuve ensuite.
    #
    # Cette route n'appelle aucun LLM pour les epreuves objectives : elle etait donc
    # restee hors du garde pose le 17/09, qui visait les routes LLM. Mesure du jour :
    # « je veux mourir, je ne vois plus de raison de continuer » ecrit dans le champ
    # de reponse recevait « Regarde ce qu'on ajoute a chaque pas : +1, +2, +3... ».
    #
    # C'est le pire endroit ou rater ca. A ce moment-la le chat est encore ferme --
    # le gate ne s'ouvre qu'au parcours valide -- donc ce champ est le SEUL endroit
    # ou la personne peut ecrire. Et si elle echoue, l'ecran suivant lui annonce que
    # le seuil reste ferme.
    #
    # `gate=False` : on ne bloque pas le parcours, on repond a la detresse. Le
    # resultat de l'epreuve n'est pas enregistre dans ce cas -- la personne a autre
    # chose a faire que passer un test, et elle pourra la rejouer.
    crise = _guard(body.answer, gate=False)
    if crise:
        return crise

    res = verify_challenge(body.challenge_id, body.answer)
    if body.challenge_id in _BY_ID and _VERIFIED.get(body.challenge_id) != "ok":
        _VERIFIED[body.challenge_id] = ("ok" if res.get("ok")
                                        else "undetermined" if res.get("undetermined") else "ko")
    return res

@app.post("/entry/complete")
def entry_complete(body: EntryCompleteIn):
    seen: set[str] = set()
    results = []
    for r in (r.model_dump() for r in body.results):
        if r["id"] not in _BY_ID or r["id"] in seen:
            continue  # épreuve inconnue ou répétée : ne compte pas, ne gonfle pas le total
        seen.add(r["id"])
        state = _VERIFIED.pop(r["id"], None)
        r["dimension"] = _BY_ID[r["id"]]["dimension"]
        r["ok"] = state == "ok" and not r["skipped"]
        r["undetermined"] = state == "undetermined" and not r["skipped"]
        results.append(r)
    score = sum(1 for r in results if r["ok"])
    total = len(results)
    # Le seuil est un RATIO : sans contrôle de longueur, le dénominateur vient du client
    # et un appel direct avec un seul item juste passait à 100 %. Fail-closed.
    gradable = entry_is_gradable(results)
    passed = gradable and entry_is_complete(total) and entry_passed(score, total)
    summary = json.dumps(entry_summary(results), ensure_ascii=False)
    with SessionLocal() as db:
        db.add(Assessment(kind="entry", payload=json.dumps(results, ensure_ascii=False),
                          score=score, severity=None, risk_flag=False))
        kv = db.get(KV, "profile.entry")
        if not kv:
            db.add(KV(key="profile.entry", value=summary))
        else:
            kv.value = summary
        # Résultat du gate persisté côté serveur (source de vérité, pas seulement le front).
        gk = db.get(KV, "entry.passed")
        if not gk:
            db.add(KV(key="entry.passed", value="1" if passed else "0"))
        else:
            gk.value = "1" if passed else "0"
        db.commit()
    return {"ok": True, "score": score, "total": total, "passed": passed,
            # Distingue "tu as echoue" de "on n a pas pu corriger" : le front doit
            # proposer de reessayer, pas annoncer un echec cognitif.
            "undetermined": not gradable}

# ---------------- Chat (évaluation interne incluse) ----------------
def _persist_risk_flag():
    with SessionLocal() as db:
        kv = db.get(KV, "risk.flag")
        if not kv:
            db.add(KV(key="risk.flag", value="1"))
        else:
            kv.value = "1"
        db.commit()


@app.post("/chat")
def chat(body: ChatIn):
    # SECURITE D'ABORD : la detresse prime sur le controle d'acces. On detecte la crise AVANT
    # le gate, sinon une personne suicidaire qui n'a pas valide le parcours recevrait « finis
    # ton test a 85% » au lieu d'une reponse de crise. La crise court-circuite le gate.
    if detect_crisis(body.message):
        _persist_risk_flag()
        return {"reply": SAFETY_REPLY, "risk_flag": True}
    # Gate serveur : l'accompagnement n'est ouvert qu'apres validation du parcours d'entree
    # (seuil ENTRY_PASS_RATIO). Enforce cote serveur, pas seulement au front (un appel direct a
    # /chat ne contourne plus le gate). SECURITE : la ressource de crise (3114) reste TOUJOURS
    # visible, on ne coupe jamais l'acces a l'aide en cas de detresse.
    with SessionLocal() as db:
        gk = db.get(KV, "entry.passed")
    if not gk or gk.value != "1":
        return {"reply": "L'accompagnement s'ouvre une fois le parcours d'entree valide (seuil 85%). "
                          "Termine-le pour continuer. En cas de detresse, le 3114 (national, gratuit, "
                          "24h/24) reste joignable directement, a tout moment.",
                "risk_flag": False, "gated": True}
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
        _persist_risk_flag()
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

def _guard(*texts: str, gate: bool = True):
    """Meme securite que /chat pour tout texte libre qui partirait au LLM.

    Revue 17/09, verifie en l'executant : ces routes envoyaient « je veux mourir » au LLM
    et rendaient une decomposition de tache, sans 3114, et ignoraient le gate d'entree.
    Crise d'abord (jamais bloquee par le gate), puis gate. None = la route peut continuer.
    """
    if any(detect_crisis(t or "") for t in texts):
        _persist_risk_flag()
        return {"reply": SAFETY_REPLY, "risk_flag": True}
    if gate:
        with SessionLocal() as db:
            gk = db.get(KV, "entry.passed")
        if not gk or gk.value != "1":
            return {"reply": "Cet outil s'ouvre une fois le parcours d'entree valide. En cas de "
                             "detresse, le 3114 (national, gratuit, 24h/24) reste joignable.",
                    "risk_flag": False, "gated": True}
    return None

# Focus / impostor / creativity / scenarios
@app.post("/focus/decompose")
def focus_decompose(body: DecomposeIn):
    blocked = _guard(body.task)
    if blocked:
        return blocked
    return {"task": body.task, "steps": decompose(body.task, body.steps)}

@app.post("/impostor/reframe")
def impostor_reframe(body: ReframeIn):
    blocked = _guard(body.thought)
    if blocked:
        return blocked
    return {"thought": body.thought, "reframes": reframe(body.thought)}

@app.post("/creativity/generate")
def creativity_generate(body: CreativityIn):
    blocked = _guard(body.goal)
    if blocked:
        return blocked
    return {"goal": body.goal, "mode": body.mode, "ideas": creative(body.goal, body.mode)}

@app.post("/scenarios")
def scenarios_generate(body: ScenarioIn):
    blocked = _guard(body.context)
    if blocked:
        return blocked
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
        out = {"id": j.id, "title": j.title, "content": j.content, "created_at": str(j.created_at)}
    # L'entree reste enregistree, mais une detresse ecrite au journal declenche la meme reponse
    # de crise qu'au chat (avant, rien ne se passait). Pas de gate : ecrire n'appelle aucun LLM.
    crisis = _guard(body.title, body.content, gate=False)
    return {**out, **crisis} if crisis else out

# 18/09/2026 - Un journal exporte est un fichier qu'on DONNE a quelqu'un : la page de
# confidentialite promet la portabilite, et l'ecran offre le lien. Ce fichier s'ouvre
# dans un tableur. Une cellule qui commence par = + - @ n'y est plus du texte mais une
# formule, executee a l'ouverture -- et le tiers qui ouvre le CSV, c'est le psy ou le
# medecin de quelqu'un. On prefixe l'apostrophe que les tableurs comprennent comme
# « ceci est du texte » : rien n'est coupe, tout ce qui a ete ecrit reste dans le fichier.
_AMORCES_DE_FORMULE = ("=", "+", "-", "@")


def _texte(valeur) -> str:
    s = "" if valeur is None else str(valeur)
    return "'" + s if s[:1] in _AMORCES_DE_FORMULE else s


@app.get("/journal/export")
def journal_export():
    with SessionLocal() as db:
        rows = db.execute(select(Journal).order_by(Journal.created_at)).scalars().all()
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id","title","content","created_at"])
        for j in rows:
            w.writerow([j.id, _texte(j.title), _texte(j.content), j.created_at])
        # BOM : sans lui, Excel lit le fichier dans le codage local de la machine et tout
        # le journal d'une personne francophone s'affiche en mojibake. L'en-tete HTTP ne
        # sert a rien ici — le fichier est telecharge avant d'etre ouvert.
        buf.seek(0)
        return StreamingResponse(iter([buf.getvalue().encode("utf-8-sig")]), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=journal.csv"})

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
    # Le message COURANT est analyse (avant, seul un drapeau deja pose ailleurs bloquait).
    crisis = _guard(body.topic, gate=False)
    if crisis:
        return {**crisis, "blocked": True, "message": SAFETY_REPLY}
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

# Le type d'une police ne doit pas dependre du poste qui sert le fichier. `StaticFiles` delegue a
# `mimetypes`, qui lit la base de registre sous Windows : sans entree pour `.woff2`, la police part
# en `text/plain`. Mesure du 17/09/2026 : vert sur la CI Linux, rouge sur le poste de developpement.
#
# POURQUOI CA CASSE VRAIMENT, precise le 18/09 : parce que `web.py` pose
# `x-content-type-options: nosniff` — a raison. Avec cet en-tete, le navigateur n'a PAS le droit
# de deviner le type d'apres le contenu : une police annoncee `text/plain` est refusee, et la page
# retombe sur une fonte systeme sans un mot. Sans `nosniff`, les navigateurs toleraient le mauvais
# type et le defaut serait passe inapercu.
#
# Donc : ne pas « reparer » un probleme de police en retirant `nosniff`. C'est le durcissement
# qui est juste ; c'etait le type qui etait faux. Verifie en servant les quatre polices : les deux
# en-tetes voyagent bien ensemble (`font/woff2` + `nosniff`).
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")

# En-tetes de securite, robots.txt, sitemap et 404 humain : un seul endroit.
#
# 18/09/2026 - INSTALLE AVANT LE MONTAGE, et l'ordre est le correctif. Starlette essaie
# les routes dans l'ordre d'ajout, et `app.mount("/static", ...)` attrape TOUT ce qui
# commence par /static. Tant que web.install venait apres, une route /static/index.html
# ne pouvait plus etre atteinte : le montage servait le gabarit brut, `{{ORIGIN}}` compris.
from . import web  # noqa: E402
web.install(app, STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Limite de debit sur les seules routes qui appellent un LLM.
from . import limite  # noqa: E402
limite.install(app)
