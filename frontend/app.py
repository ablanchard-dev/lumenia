# -*- coding: utf-8 -*-
import os
import requests
import pandas as pd
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Lumenia v2.1", page_icon="🤖", layout="wide")
st.markdown(
    """
<style>
:root { --fs: 16px; }
html, body, [class*="css"] { font-size: var(--fs) !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- Helpers API ----------------
def api_get(path):
    try:
        r = requests.get(f"{BACKEND}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        st.error(f"Backend injoignable sur {BACKEND}{path}. Lance le backend d'abord (port 8000).")
        st.stop()

def api_post(path, payload=None, params=None):
    """POST helper that can send either JSON payload or query params."""
    try:
        r = requests.post(f"{BACKEND}{path}", json=payload, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        st.error(f"Backend injoignable sur {BACKEND}{path}.")
        st.stop()
# ---------------------------------------------

st.sidebar.title("Lumenia v2.1")
st.sidebar.caption("MVP non médical – données locales")

# -------- Consent gating (FIX) --------
server_cons = api_get("/consent").get("accepted", False)
# aligne l'état local sur le serveur si différent
if st.session_state.get("consent_accepted") != server_cons:
    st.session_state["consent_accepted"] = server_cons

cons = st.session_state.get("consent_accepted", False)

with st.sidebar.expander("Consentement & Confidentialité", expanded=not cons):
    st.write("Lumenia n’est pas un dispositif médical. Les données restent locales (SQLite).")
    agree = st.checkbox("Je comprends et j’accepte", value=cons)
    if st.button("Valider le consentement"):
        # IMPORTANT : envoyer accepted en query param, pas dans le JSON
        resp = api_post("/consent", params={"accepted": bool(agree)})
        st.session_state["consent_accepted"] = resp.get("accepted", bool(agree))
        st.rerun()

if not st.session_state.get("consent_accepted", False):
    st.warning("Veuillez accepter le consentement pour utiliser l’application.")
    st.stop()
# -------------------------------------

# Risk banner
risk_flag = api_get("/risk").get("risk_flag", False)
if risk_flag:
    st.error("Signal de prudence actif (PHQ-9). En cas d’urgence : 3114 / 15 / 112.")

tabs = st.tabs([
    "Profil", "Assessment", "Focus", "Anti-imposteur",
    "Créativité", "Scénarios", "Journal / Export", "Ressources", "Psy Coach"
])

# ---------------- Profil ----------------
with tabs[0]:
    prof = api_get("/profile")
    st.subheader("Profil neuro-adaptatif")
    c1, c2, c3 = st.columns(3)
    with c1:
        low = st.checkbox("Mode faible stimulation", value=prof["low_stim"])
    with c2:
        fs = st.slider("Taille de police", 12, 28, prof["font_size"])
    with c3:
        pacing = st.selectbox(
            "Rythme",
            ["slow", "normal", "fast"],
            index=["slow", "normal", "fast"].index(prof["pacing"])
        )
    if st.button("Enregistrer le profil"):
        api_post("/profile", {"low_stim": low, "font_size": fs, "pacing": pacing})
        st.toast("Profil enregistré ✅")
    st.markdown(f"<style>:root {{ --fs: {fs}px; }}</style>", unsafe_allow_html=True)
    if st.button("Adapter l’interface"):
        tips = api_post("/adapt", {"low_stim": low, "font_size": fs, "pacing": pacing})["ui_tips"]
        st.write("Suggestions UI :", tips)

# ---------------- Assessment ----------------
with tabs[1]:
    st.subheader("Évaluations")
    cA, cB = st.columns(2)
    with cA:
        st.write("Test d’entrée (rapide)")
        att  = st.slider("Attention soutenue", 0, 4, 2, key="entry_att")
        sens = st.slider("Sensibilité sensorielle", 0, 4, 2, key="entry_sens")
        org  = st.slider("Organisation", 0, 4, 2, key="entry_org")
        soc  = st.slider("Socio-émotionnel", 0, 4, 2, key="entry_soc")
        if st.button("Valider test d’entrée", key="btn_entry"):
            st.write(api_post("/assessment/entry", {
                "answers": {"attention": att, "sensory": sens, "organization": org, "social": soc}
            }))

    with cB:
        st.write("PHQ-9")
        phq = [
            st.slider(f"PHQ-9 – Item {i+1}", 0, 3, 0, key=f"phq_{i}")
            for i in range(9)
        ]
        if st.button("Calculer PHQ-9", key="btn_phq"):
            r = api_post("/assessment/phq9", {"items": phq, "item9": phq[8]})
            st.write(r)

        st.write("GAD-7")
        gad = [
            st.slider(f"GAD-7 – Item {i+1}", 0, 3, 0, key=f"gad_{i}")
            for i in range(7)
        ]
        if st.button("Calculer GAD-7", key="btn_gad"):
            st.write(api_post("/assessment/gad7", {"items": gad}))

# ---------------- Focus ----------------
with tabs[2]:
    st.subheader("Décomposer une tâche")
    task = st.text_input("Ta tâche")
    steps = st.slider("Nombre d’étapes", 2, 12, 5)
    if st.button("Décomposer"):
        st.write(api_post("/focus/decompose", {"task": task, "steps": steps})["steps"])

# -------------- Anti-imposteur --------------
with tabs[3]:
    st.subheader("Reformuler une pensée")
    th = st.text_area("Pensée actuelle")
    if st.button("Reformuler"):
        st.write(api_post("/impostor/reframe", {"thought": th})["reframes"])

# ---------------- Créativité ----------------
with tabs[4]:
    st.subheader("Générateur créatif")
    goal = st.text_input("But / thème")
    mode = st.selectbox("Mode", ["ideas", "analogies", "prompts"])
    if st.button("Générer"):
        st.write(api_post("/creativity/generate", {"goal": goal, "mode": mode})["ideas"])

# ---------------- Scénarios ----------------
with tabs[5]:
    st.subheader("Scénarios / scripts")
    ctx = st.text_input("Contexte")
    style_choice = st.selectbox("Style", ["assertif", "neutre", "supportif"])
    if st.button("Proposer"):
        st.write(api_post("/scenarios", {"context": ctx, "style": style_choice})["scripts"])

# ---------------- Journal ----------------
with tabs[6]:
    st.subheader("Journal & export")
    title = st.text_input("Titre")
    content = st.text_area("Contenu")
    c = st.columns(2)
    if c[0].button("Ajouter"):
        api_post("/journal", {"title": title, "content": content})
        st.toast("Ajouté 📓")
    data = api_get("/journal")
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        csv = requests.get(f"{BACKEND}/journal/export").text
        st.download_button("Exporter CSV", data=csv, file_name="journal.csv", mime="text/csv")
    else:
        st.info("Journal vide.")

# --------------- Ressources ---------------
with tabs[7]:
    st.subheader("Ressources utiles (France)")
    st.write(api_get("/resources")["fr"])

# ---------------- Psy Coach ----------------
with tabs[8]:
    st.subheader("Psy Coach (non médical)")
    if risk_flag:
        st.error("Prudence : génération limitée (PHQ-9 item 9 > 0).")
    topic = st.text_input("Sujet")
    style_pc = st.selectbox("Style", ["brief", "supportif", "structuré"])
    if st.button("Conseiller"):
        out = api_post("/psy/coach", {"topic": topic, "style": style_pc})
        if out.get("blocked"):
            st.warning(out["message"])
        else:
            st.write(out["advice"])
