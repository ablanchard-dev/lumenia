# -*- coding: utf-8 -*-
"""Le droit à la portabilité doit désigner une surface qui l'offre vraiment.

18/09/2026. La page de confidentialité annonce les six droits du RGPD, puis
ajoute une phrase qui est la seule à dire **comment** en exercer un :

    « Le journal est d'ailleurs exportable directement depuis l'application. »

Mesure : `static/app.js` — l'interface servie à `/`, celle que lit quelqu'un qui
ouvre `/confidentialite` — ne contient **ni « journal » ni « export »**, zéro
occurrence. L'export existe bien (`/journal/export`, et un bouton « Exporter
CSV » dans l'interface Streamlit), mais le README qualifie lui-même cette
interface de *superseded*, et personne n'y arrive depuis l'écran de chat.

La phrase n'est donc pas fausse : elle est **vraie d'une autre application que
celle qu'on a sous les yeux**. C'est pire qu'une erreur visible — la personne
cherche un bouton qui n'existe pas dans son écran, et conclut que le droit
annoncé est décoratif.

La règle tenue ici : si la page dit où exporter, cet endroit doit exister pour
qui lit. Soit l'interface servie appelle vraiment la route d'export — et la
formule « depuis l'application » redevient exacte, le test s'en aperçoit tout
seul — soit la phrase nomme la surface qui l'offre.
"""
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = RACINE / "static" / "confidentialite.html"
SPA = RACINE / "static" / "app.js"
ACCUEIL = RACINE / "static" / "index.html"

ROUTE = "/journal/export"


def _passage_des_droits() -> str:
    """Le paragraphe qui porte les droits, lignes recollées.

    Recoller AVANT de chercher : le HTML passe à la ligne au milieu de ses
    phrases, et « depuis l'application » peut se retrouver coupé en deux.
    """
    html = PAGE.read_text(encoding="utf-8")
    paragraphes = [" ".join(p.split()) for p in re.findall(r"<p>(.*?)</p>", html, re.S)]
    portabilite = [p for p in paragraphes if "portabilit" in p.lower()]
    assert portabilite, "la page n'annonce plus le droit à la portabilité"
    return portabilite[0]


def _la_spa_sait_exporter() -> bool:
    """L'interface servie, c'est `index.html` ET `app.js`.

    Un lien `<a href="/journal/export" download>` offre l'export aussi bien
    qu'un `fetch()` — et sans une ligne de JavaScript. Ne regarder que `app.js`
    aurait fait rater le geste le plus simple.
    """
    return any(ROUTE in f.read_text(encoding="utf-8") for f in (SPA, ACCUEIL))


def test_le_crible_lit_bien_les_deux_surfaces():
    """Témoin : sans lui, un fichier déplacé rendrait le test suivant vert sur du vide."""
    passage = _passage_des_droits()

    assert "effacement" in passage, passage
    assert len(SPA.read_text(encoding="utf-8")) > 1000, "app.js est vide ou introuvable"


def test_la_phrase_sur_l_export_designe_une_surface_qui_existe():
    passage = _passage_des_droits()
    if "export" not in passage.lower():
        return  # la page ne dit plus où exporter : rien à tenir ici.

    # Soit l'interface servie sait le faire, soit la phrase dit où c'est.
    designe_ailleurs = ROUTE in passage or "streamlit" in passage.lower()

    assert _la_spa_sait_exporter() or designe_ailleurs, (
        "la page annonce un export du journal sans que l'interface servie (`static/app.js`) "
        f"n'appelle {ROUTE}, et sans nommer la surface qui l'offre. La portabilité est un "
        "droit : une phrase qui renvoie à un écran absent le rend décoratif — "
        f"passage lu : {passage}"
    )


def test_la_route_d_export_existe_toujours_quelque_part():
    """Une phrase exacte aujourd'hui deviendrait fausse si la route disparaissait."""
    from app.main import app

    chemins = {r.path for r in app.routes if getattr(r, "methods", None)}

    assert ROUTE in chemins, (
        f"{ROUTE} n'existe plus : la page de confidentialité promet une portabilité "
        "que plus rien ne rend possible"
    )


# ---------------------------------------------------------------------------
# 18/09/2026, suite. Le test ci-dessus laissait le choix : soit l'interface
# servie exporte, soit la page nomme la surface qui le fait. La deuxieme branche
# etait un constat, pas une cible -- elle disait « le droit existe, mais pas ici ».
#
# L'export vit desormais DANS l'interface servie, en un lien discret de la barre
# laterale. Ce test-ci ne laisse plus le choix : c'est la decision produit du
# tour, et la reprendre doit couter un rouge.
# ---------------------------------------------------------------------------


def test_l_interface_servie_offre_elle_meme_l_export():
    assert _la_spa_sait_exporter(), (
        "l'ecran ou la personne ecrit ne propose plus d'exporter ses donnees. La "
        "portabilite redevient alors un droit qu'il faut demander par courrier, "
        "alors que le serveur sait deja rendre le fichier"
    )


def test_l_export_n_est_pas_l_action_principale_de_l_ecran():
    """Un seul CTA : exporter est un droit, pas ce qu'on vient faire ici.

    Le lien doit rester discret — sinon il entre en concurrence avec l'action
    qui compte (ecrire), et la regle du CTA unique tombe.
    """
    html = ACCUEIL.read_text(encoding="utf-8")
    bloc = html[html.find(ROUTE) - 400: html.find(ROUTE) + 200]

    assert "btn-primary" not in bloc, "l'export ne doit pas etre presente comme l'action principale"
