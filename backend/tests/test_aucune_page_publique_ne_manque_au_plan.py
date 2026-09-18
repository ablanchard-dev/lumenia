# -*- coding: utf-8 -*-
"""Le sitemap est tenu dans les DEUX sens, pas seulement dans le sien.

18/09/2026. Le lien sitemap → page est déjà gardé : chaque adresse du plan doit
répondre 200 (`test_aucun_lien_ne_tombe_dans_le_vide`), et les pages légales
doivent y figurer (`test_pages_legales`). L'autre sens ne l'était pas : **une
page servie par l'application et absente du plan**.

Ce n'est pas une omission théorique. `app/web.py` porte cette phrase :

    « Une seule liste : le sitemap ne peut pas oublier une page que le site sert. »

Elle décrit une structure qui n'existe pas. `PAGES` alimente le sitemap, mais
les routes, elles, sont écrites à la main ailleurs — `/cgu` et
`/confidentialite` dans ce fichier, `/` dans `app/main.py`. Rien ne relie les
deux : ajouter une page, c'est deux gestes, et le second s'oublie.

Et l'oubli ne coûte pas seulement le référencement. `robots.txt` déduit sa liste
d'API de tout ce qui n'est PAS dans `PAGES` : une page publique absente de
`PAGES` n'est pas juste ignorée des moteurs, elle est activement `Disallow:`.
Sur une application de santé mentale, la page que personne ne trouve peut être
celle qui porte le 3114.

Mesure avant d'écrire, sans défaut trouvé : trois pages servies, trois au plan,
zéro accusation. La discipline tenait à la main.
"""
import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Les pages de documentation de FastAPI : servies en HTML, mais ce n'est pas le
# site. Le test de surface d'API les écarte déjà par la même liste.
OUTILS = {"/docs", "/redoc", "/docs/oauth2-redirect"}


def _pages_servies() -> set[str]:
    """Ce que l'application rend VRAIMENT en HTML — pas ce qu'elle déclare.

    On interroge chaque route plutôt que de lire une liste : une page ajoutée
    demain entre d'elle-même dans le crible, ce qui est précisément la propriété
    qui manquait.
    """
    servies = set()
    for route in app.routes:
        methodes = getattr(route, "methods", None)
        if not methodes or "GET" not in methodes:
            continue
        if route.path.startswith("/static") or "{" in route.path or route.path in OUTILS:
            continue
        reponse = client.get(route.path)
        if reponse.status_code == 200 and "text/html" in reponse.headers.get("content-type", ""):
            servies.add(route.path)
    return servies


def _plan() -> set[str]:
    xml = client.get("/sitemap.xml").text
    # On garde le chemin, pas l'origine : `PUBLIC_ORIGIN` change d'un
    # déploiement à l'autre et le test n'a rien à dire là-dessus.
    return {re.sub(r"^https?://[^/]+", "", loc) or "/" for loc in re.findall(r"<loc>([^<]+)</loc>", xml)}


def test_le_crible_voit_bien_des_pages_servies():
    """Témoin : un crible qui ne trouve rien rendrait le test suivant vert sur le vide."""
    servies = _pages_servies()

    assert "/" in servies, servies
    assert len(servies) >= 3, servies


def test_le_crible_lit_bien_le_plan():
    plan = _plan()

    assert "/" in plan, plan


def test_aucune_page_servie_ne_manque_au_plan():
    oubliees = sorted(_pages_servies() - _plan())

    assert oubliees == [], (
        f"ces pages sont servies en HTML et absentes du sitemap : {oubliees}. "
        "Elles ne sont pas seulement invisibles aux moteurs : `robots.txt` déduit sa liste "
        "d'API de tout ce qui n'est pas au plan, donc une page publique oubliée est "
        "activement interdite d'indexation"
    )


def test_le_plan_ne_promet_aucune_page_que_le_site_ne_sert_pas():
    """L'autre sens, déjà tenu ailleurs, gardé ici aussi : un plan qui ment sur
    ce qui existe fait perdre du crédit à toutes ses autres adresses."""
    fantomes = sorted(chemin for chemin in _plan() if client.get(chemin).status_code != 200)

    assert fantomes == [], f"le sitemap annonce des adresses qui ne répondent pas : {fantomes}"
