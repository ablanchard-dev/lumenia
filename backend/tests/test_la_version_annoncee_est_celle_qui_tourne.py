# -*- coding: utf-8 -*-
"""Une seule version, deux surfaces — et rien ne les tenait ensemble.

18/09/2026. Le numéro de version de Lumenia était écrit **deux fois à la main**,
dans le même fichier :

    app = FastAPI(title="LumenIa Backend", ..., version="2.3.0")   # → /openapi.json
    def healthz(): return {"ok": True, "version": "2.3.0"}          # → /healthz

Les deux disaient la même chose ce jour-là. C'est exactement l'état dans lequel
étaient le compte de commits de `GATES.md` (16 annoncés, 137 réels) et le
« three things persist » du README (pour quatre tables) avant de dériver : un
chiffre juste que rien ne tient n'est pas garanti, il est seulement encore jeune.

Et la dérive coûterait quelque chose de précis. `/healthz` est ce qu'un
superviseur interroge pour savoir **quelle version tourne** ; `/openapi.json` est
ce qu'un client lit pour savoir **à quoi il parle**. Deux réponses différentes à
la même question, c'est un déploiement qu'on croit fait.

Le correctif enlève la deuxième main : une constante, deux usages. Ce test tient
la promesse même si quelqu'un réécrit un littéral demain — il ne compare pas à un
numéro figé, il compare les deux surfaces entre elles.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SOURCE = Path(__file__).resolve().parent.parent / "app" / "main.py"


def test_le_crible_voit_bien_une_version():
    """Témoin : sans lui, une route renommée rendrait le test suivant vert sur du vide."""
    corps = client.get("/healthz").json()

    assert "version" in corps, corps
    assert re.fullmatch(r"\d+\.\d+\.\d+", str(corps["version"])), corps
    assert app.version, "l'application n'annonce plus de version dans son schéma"


def test_healthz_et_le_schema_annoncent_la_meme_version():
    sante = client.get("/healthz").json()["version"]

    assert sante == app.version, (
        f"/healthz annonce {sante} et le schéma OpenAPI {app.version}. Un superviseur "
        "interroge le premier pour savoir quelle version tourne, un client lit le second "
        "pour savoir à quoi il parle : deux réponses, c'est un déploiement qu'on croit fait"
    )


def test_la_version_n_est_ecrite_qu_une_fois_dans_le_code():
    """La garantie structurelle : deux littéraux identiques dérivent tôt ou tard.

    On compte les numéros de version en dur dans le module. Un seul est permis —
    celui de la constante. Le jour où quelqu'un en recolle un second, ce test
    rougit avant que les deux ne divergent, pas après.
    """
    code = SOURCE.read_text(encoding="utf-8")
    # Les littéraux de version : trois nombres séparés par des points, entre guillemets.
    litteraux = re.findall(r"""["'](\d+\.\d+\.\d+)["']""", code)

    assert len(litteraux) <= 1, (
        f"la version est écrite {len(litteraux)} fois en dur dans `app/main.py` : {litteraux}. "
        "Une valeur déclarée à deux endroits est tenue par la mémoire de celui qui la change — "
        "elle finit par dire deux choses différentes"
    )
