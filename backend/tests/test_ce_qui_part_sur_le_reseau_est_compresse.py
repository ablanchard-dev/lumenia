# -*- coding: utf-8 -*-
"""Le navigateur demande gzip ; le serveur doit le lui donner.

18/09/2026. Mesure du premier chargement de l'accueil : 71,4 Ko de texte
(index.html, style.css, app.js) partaient **bruts** alors que toute requête de
navigateur annonce `Accept-Encoding: gzip`. Compressés, les mêmes octets pèsent
20,4 Ko — **51 Ko de moins, 71 %**.

Ce n'est pas une optimisation de confort. Lumenia s'adresse à des personnes en
détresse, souvent depuis un téléphone, parfois en 3G ou sur un forfait compté.
Cinquante kilo-octets sur un lien lent, c'est plusieurs secondes devant un écran
blanc, au moment précis où quelqu'un cherche le 3114.

**Pourquoi ce n'était pas déjà fait, et pourquoi c'est sûr ici.** Compresser une
réponse chiffrée peut exposer un secret qu'elle contient (attaque BREACH) : le
volume compressé varie selon que l'entrée de l'attaquant ressemble ou non au
secret. L'attaque exige donc un secret DANS la réponse. Lumenia n'en met aucun :
ni cookie de session, ni jeton CSRF — la checklist d'Alex bannit les cookies, et
c'est ce choix-là qui rend la compression inoffensive. Le test le vérifie plutôt
que de le croire : si un `set_cookie` apparaît un jour, il rougit.
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

RACINE = Path(__file__).resolve().parent.parent
client = TestClient(app)

# Les trois ressources du premier chargement : ce que coûte l'accueil, en texte.
TEXTES = ("/", "/static/style.css", "/static/app.js")


def _octets_sur_le_reseau(chemin: str, *, compresse: bool) -> int:
    """Ce qui passe VRAIMENT sur le lien, pas ce que le client en fait ensuite.

    Premier essai : `len(reponse.content)`. Il donnait le même chiffre avant et
    après la compression, parce que le client de test décode gzip tout seul — la
    mesure portait sur le corps décodé, c'est-à-dire sur rien du tout. Un test qui
    ne bouge pas quand le produit change n'est pas un test.

    `Content-Length` est posé par le serveur après compression : c'est le nombre
    d'octets que le téléphone télécharge réellement.
    """
    entetes = {"Accept-Encoding": "gzip"} if compresse else {"Accept-Encoding": "identity"}
    reponse = client.get(chemin, headers=entetes)
    assert reponse.status_code == 200, chemin

    longueur = reponse.headers.get("content-length")
    assert longueur is not None, f"{chemin} ne dit pas sa taille : impossible de la mesurer"
    return int(longueur)


def test_le_crible_voit_bien_des_ressources_a_peser():
    """Témoin : sans poids réel, tout ce qui suit serait vert sur du vide."""
    brut = sum(_octets_sur_le_reseau(c, compresse=False) for c in TEXTES)

    assert brut > 40_000, f"le premier chargement pèse {brut} octets : le crible ne lit rien"


@pytest.mark.parametrize("chemin", TEXTES)
def test_chaque_ressource_texte_part_compressee(chemin):
    reponse = client.get(chemin, headers={"Accept-Encoding": "gzip"})

    assert reponse.headers.get("content-encoding") == "gzip", (
        f"{chemin} part brut alors que le client annonce gzip. Sur un lien lent, "
        "c'est du temps devant un écran blanc pour quelqu'un qui cherche le 3114"
    )


def test_le_premier_chargement_tient_sous_trente_kilo_octets():
    """Le chiffre que le produit doit tenir, mesuré sur ce qui part vraiment.

    Borne posée à 30 Ko : la mesure du jour donne 20,4 Ko compressés, la marge
    absorbe une page qui s'étoffe sans laisser passer un doublement silencieux.
    """
    pese = sum(_octets_sur_le_reseau(c, compresse=True) for c in TEXTES)

    assert pese < 30_000, (
        f"le premier chargement pèse {pese/1024:.1f} Ko compressés. "
        "Au-delà, l'accueil met plusieurs secondes à s'afficher en 3G"
    )


def test_la_compression_gagne_vraiment_la_moitie():
    """Un `Content-Encoding: gzip` sur une réponse non réduite serait décoratif."""
    brut = sum(_octets_sur_le_reseau(c, compresse=False) for c in TEXTES)
    compresse = sum(_octets_sur_le_reseau(c, compresse=True) for c in TEXTES)

    assert compresse < brut / 2, f"{brut} -> {compresse} : la compression ne rend presque rien"


def test_aucune_reponse_ne_transporte_de_secret_compressible():
    """La condition qui rend la compression sûre, vérifiée et non supposée.

    BREACH exige un secret dans la réponse compressée. Le jour où Lumenia pose un
    cookie de session ou un jeton CSRF, cette hypothèse tombe, et ce test doit
    rougir AVANT que le secret ne voyage compressé.
    """
    sources = "\n".join(
        f.read_text(encoding="utf-8-sig") for f in sorted((RACINE / "app").glob("*.py"))
    )
    assert len(sources) > 10_000, "le crible ne lit pas les sources de l'application"

    poseurs = re.findall(r"set_cookie|csrf_token|CSRFToken", sources)

    assert poseurs == [], (
        f"l'application pose maintenant un secret dans ses réponses ({set(poseurs)}), et "
        "ces réponses sont compressées : c'est la condition de l'attaque BREACH. "
        "Excluez ces réponses de la compression, ou ajoutez un masque par requête"
    )
