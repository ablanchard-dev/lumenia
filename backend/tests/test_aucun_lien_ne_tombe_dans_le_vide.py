# -*- coding: utf-8 -*-
"""Un lien qui ne mène nulle part, sur une appli de santé mentale.

18/09/2026. La page 404 de Lumenia est soignée : elle rend une vraie page, elle
porte le 3114. C'est précisément ce qui rend un lien cassé **silencieux** — rien
ne lève, rien ne rougit, et la personne qui cherchait « mes données » atterrit
sur un écran d'excuses.

Mesure du jour : les huit cibles internes servies répondent toutes 200, et aucun
chemin du script front ne désigne une route qui n'existe pas. Il n'y a donc pas
de défaut — mais rien ne le tenait. Un `href="/aide"` ajouté demain partirait
sans bruit, et c'est le genre de lien qu'on ajoute en dernier, sans y penser.

Le crible couvre les deux surfaces : ce que le serveur **sert** (href et src des
pages publiques, suivis par une vraie requête) et ce que le front **appelle**
(les chemins littéraux de `app.js`, confrontés aux routes déclarées).
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

RACINE = Path(__file__).resolve().parent.parent
client = TestClient(app)

# Un lien sortant, un numéro de téléphone ou une ancre ne se vérifient pas ici :
# le premier dépend du réseau, les deux autres ne sont pas des requêtes.
HORS_PORTEE = ("http://", "https://", "tel:", "mailto:", "#", "data:", "//")


def _pages_publiques() -> list[str]:
    """Les pages du sitemap, pas une liste tenue à la main : une page ajoutée au
    sitemap demain entre d'elle-même dans le crible."""
    plan = client.get("/sitemap.xml")
    assert plan.status_code == 200, "le sitemap est la source des pages publiques"
    chemins = {
        re.sub(r"^https?://[^/]+", "", url) or "/"
        for url in re.findall(r"<loc>([^<]+)</loc>", plan.text)
    }
    return sorted(chemins)


def _cibles_internes() -> dict[str, set[str]]:
    """Chaque href/src interne, avec les pages où il apparaît (pour le message)."""
    trouvees: dict[str, set[str]] = {}
    for page in _pages_publiques():
        reponse = client.get(page)
        assert reponse.status_code == 200, f"{page} est au sitemap mais ne se sert pas"
        for cible in re.findall(r'(?:href|src)="([^"]+)"', reponse.text):
            if cible.startswith(HORS_PORTEE):
                continue
            trouvees.setdefault(cible, set()).add(page)
    return trouvees


def test_le_crible_voit_bien_des_cibles_a_verifier():
    """Sans ce témoin, un motif cassé rendrait le test suivant vert sur le vide."""
    cibles = _cibles_internes()

    assert len(cibles) >= 5, cibles
    assert "/cgu" in cibles, "le pied de page doit mener aux CGU"


def test_le_crible_sait_dire_non():
    """Témoin inverse : si tout répondait 200, le crible ne dirait jamais rien."""
    assert client.get("/une-page-qui-n-existe-pas").status_code == 404


def test_aucun_lien_interne_ne_tombe_dans_le_vide():
    morts = {
        cible: sorted(pages)
        for cible, pages in _cibles_internes().items()
        if client.get(cible, follow_redirects=False).status_code >= 400
    }

    assert morts == {}, (
        "ces liens mènent à la page 404 : elle est soignée, donc personne ne "
        f"verra que c'est une erreur — {morts}"
    )


def test_la_feuille_de_style_ne_reclame_aucun_fichier_absent():
    """Troisième surface, la plus discrète : les `url(...)` du CSS.

    Les quatre polices vivent là. Une police qui ne se sert plus ne casse rien
    de visible — la page retombe sur une fonte système, sans un mot.
    """
    feuille = client.get("/static/style.css")
    assert feuille.status_code == 200

    cibles = {
        cible
        for cible in re.findall(r"""url\(['"]?([^'")]+)['"]?\)""", feuille.text)
        if not cible.startswith(HORS_PORTEE)
    }
    assert len(cibles) >= 4, f"le crible doit voir au moins les polices : {cibles}"

    morts = sorted(c for c in cibles if client.get(c).status_code >= 400)
    assert morts == [], f"la feuille de style réclame des fichiers qui ne se servent pas : {morts}"


def test_le_script_front_n_appelle_que_des_routes_qui_existent():
    """L'autre moitié du sujet : un lien mort peut vivre dans le JavaScript.

    Une route renommée côté serveur laisse le front appeler l'ancienne, et
    l'écran reste vide sans que rien ne rougisse côté tests.
    """
    declarees = {route.path for route in app.routes if getattr(route, "path", None)}
    script = (RACINE / "static" / "app.js").read_text(encoding="utf-8")

    orphelins = []
    for chemin in sorted(set(re.findall(r"""["'`](/[A-Za-z0-9_\-/{}$.]*)["'`]""", script))):
        if chemin in declarees:
            continue
        # Un chemin bâti par interpolation (`/journal/${id}`) ou un fichier servi
        # par un montage statique : on vérifie le préfixe, puis la requête réelle.
        prefixe = chemin.split("${")[0].rstrip("/")
        if prefixe and any(route.startswith(prefixe) for route in declarees):
            continue
        if client.get(chemin, follow_redirects=False).status_code < 400:
            continue
        orphelins.append(chemin)

    assert orphelins == [], f"le front appelle des chemins que le serveur ne sert pas : {orphelins}"


@pytest.mark.parametrize("page", ["/", "/confidentialite", "/cgu"])
def test_les_pages_nommees_dans_les_tests_sont_bien_au_sitemap(page):
    """Le crible ne vaut que par ce qu'il parcourt : si une page publique sortait
    du sitemap, elle sortirait du crible sans que personne ne le remarque."""
    assert page in _pages_publiques()
