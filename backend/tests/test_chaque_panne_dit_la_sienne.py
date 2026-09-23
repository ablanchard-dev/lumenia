"""23/09/2026 — Une panne, sa phrase.

Mesuré dans un navigateur, en simulant le serveur : « trop de demandes » (429), « session
perdue » (401), « souci du serveur » (500) et « coupure réseau » affichaient TOUS la même
phrase : « Impossible de joindre le serveur. Vérifie que le backend tourne ». Fausse trois
fois sur quatre (le serveur avait répondu), et du jargon pour quelqu'un qui n'a jamais lancé
de backend.

Le script passe désormais toute erreur par `panne(err)`, qui distingue les cas. Ce fichier
garde que plus aucun `catch` d'appel au serveur n'écrit sa phrase à la main.
"""
import re
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "static" / "app.js").read_text(encoding="utf-8")


def test_la_fonction_distingue_les_quatre_pannes():
    corps = JS[JS.index("function panne("):]
    corps = corps[: corps.index("\n  }\n")]
    for cas in ("s === 429", "s === 401", "s >= 500", "Pas de connexion"):
        assert cas in corps, f"`panne` ne traite plus : {cas}"
    assert "3114" in corps


def test_aucune_erreur_ne_parle_encore_de_backend():
    assert "Vérifie que le backend tourne" not in JS
    assert "Erreur de connexion au serveur" not in JS


def test_chaque_catch_d_appel_serveur_passe_par_panne():
    # Chaque `catch (err)` du script est une panne d'appel au serveur montrée à la personne.
    blocs = re.findall(r"\} catch \(err\) \{([\s\S]{0,200})", JS)
    assert len(blocs) >= 4, "témoin : consentement, parcours, épreuve et chat doivent être vus"
    assert all("panne(err" in b for b in blocs)
