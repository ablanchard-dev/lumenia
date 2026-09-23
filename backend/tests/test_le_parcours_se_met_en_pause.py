"""Le parcours se met en pause et se reprend là où on l'a laissé, sur ce navigateur.

23/09/2026 — critique Impeccable (L-UI-3) : aucune sortie calme d'un parcours de 30 épreuves. La
progression ne vivait qu'en mémoire : recharger la page ou partir, c'était tout recommencer sur un
nouveau tirage. Pour ce public, le groupe COGA du W3C range l'absence de « reprendre plus tard »
parmi les obstacles.

Reprendre ne doit PAS retirer un parcours : `GET /entry/parcours` efface ce que le serveur a constaté
(garde du 17/09). La reprise part donc de la sauvegarde locale, sans appeler cette route.
"""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_un_bouton_de_pause_existe_sur_l_ecran_d_epreuve():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    ecran = re.search(r'<section id="screen-challenge".*?</section>', html, re.S)
    assert ecran, "témoin : l'écran d'épreuve doit exister"
    assert 'id="challenge-pause"' in ecran.group(0)


def test_le_parcours_est_garde_et_repris_sans_retirer_un_nouveau_tirage():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "lumenia.parcours" in js, "le parcours n'est jamais sauvegardé"
    debut = js.index("async function startParcours")
    corps = js[debut:js.index("\n  }\n", debut)]
    reprise = corps.find("lumenia.parcours") if "lumenia.parcours" in corps else corps.find("parcoursGarde")
    tirage = corps.find('api("/entry/parcours"')
    assert reprise != -1, "startParcours ne regarde pas la sauvegarde"
    assert tirage != -1, "témoin : le tirage doit rester possible"
    assert reprise < tirage, "la sauvegarde doit être lue AVANT de retirer un parcours"
