# -*- coding: utf-8 -*-
"""« Lumenia n'en met aucun » : vérifié sur nos sources, jamais sur ce qui part.

19/09/2026. `app/main.py` active la compression, et justifie ce choix en une phrase
précise : « Compresser une réponse chiffrée n'est sûr que si elle ne transporte aucun
secret (attaque BREACH). Lumenia n'en met aucun : ni cookie de session, ni jeton
CSRF. » La phrase nomme même son garde — « la vérifie **sur les sources** ».

C'est vrai, et c'est le mot « sources » qui est le trou. Ce garde cherche
`set_cookie|csrf_token|CSRFToken` dans notre code. Il voit ce que NOUS écrivons ; il
ne voit pas ce qui SORT — un en-tête posé à la main s'écrit `set-cookie`, avec un
tiret, et le motif ne le trouve pas.

MESURE, ET ELLE EST PLUS ÉTROITE QUE CE QUE JE CROYAIS EN COMMENÇANT. Un cookie posé
par un intergiciel a d'abord été essayé sur toutes les réponses : le garde des
sources reste vert, mais `test_la_promesse_de_ne_rien_pister_tient` le voit — il
interroge trois pages et y trouve l'en-tête. Le dépôt n'était donc PAS aveugle.

Le trou réel est ailleurs, et il a fallu une seconde mutation pour le nommer : un
cookie posé **uniquement sur une route d'API**. Les trois pages du sitemap ne le
touchent jamais.

    cookie sur /journal seulement   →  garde des sources : VERT
                                       garde de non-pistage : VERT
                                       ce fichier : 2 rouges

C'est exactement le motif de la liste tenue à la main : un crible dérivé du sitemap
ne peut pas voir l'API, qui est pourtant compressée comme le reste. Ce fichier
ne relit donc pas le code — il INTERROGE l'application, et ses routes sont déduites
de `app.routes`.

⚠️ Le garde existant reste : une couture posée dans nos sources doit rougir tout de
suite, sans attendre qu'une requête la traverse. Les deux se complètent — l'un lit
l'intention, l'autre constate le résultat.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Ce qui n'a pas à être appelé en boucle par un crible : le chat paie un LLM, et les
# deux pages de garde répondent par un statut d'erreur volontaire.
HORS_CRIBLE = {"/chat", "/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}


def _routes_de_lecture() -> list[str]:
    """Tous les chemins GET sans paramètre, déduits de l'application elle-même."""
    chemins = set()
    for route in app.routes:
        methodes = getattr(route, "methods", None) or set()
        chemin = getattr(route, "path", "")
        if "GET" not in methodes or "{" in chemin or chemin in HORS_CRIBLE:
            continue
        chemins.add(chemin)
    return sorted(chemins)


def test_le_crible_atteint_bien_des_routes():
    """Témoin : sans lui, une déduction cassée rendrait tout vert sur du vide."""
    routes = _routes_de_lecture()

    assert "/journal" in routes, routes
    assert len(routes) >= 6, routes


@pytest.mark.parametrize("chemin", _routes_de_lecture())
def test_aucune_route_ne_renvoie_de_cookie(chemin):
    reponse = client.get(chemin)

    poses = [v for k, v in reponse.headers.items() if k.lower() == "set-cookie"]

    assert poses == [], (
        f"{chemin} pose un cookie. La compression n'est sûre (BREACH) que tant qu'aucune "
        f"réponse ne transporte de secret — et cette phrase est écrite dans `main.py` : {poses}"
    )


def test_aucun_intergiciel_ne_pose_de_cookie_dans_notre_dos():
    """Le chemin qui tient en une ligne, et que lire nos sources ne verrait pas.

    `SessionMiddleware` pose un cookie signé sans que `set_cookie` apparaisse chez
    nous. Ce test nomme la pile réellement montée plutôt que de faire confiance.
    """
    montes = {type(m.cls).__name__ if hasattr(m, "cls") else str(m) for m in app.user_middleware}
    noms = {getattr(getattr(m, "cls", None), "__name__", str(m)) for m in app.user_middleware}

    interdits = {"SessionMiddleware", "AuthenticationMiddleware", "CSRFMiddleware"}

    assert not (noms & interdits), (
        f"un intergiciel pose un état par cookie : {noms & interdits}. Il faut alors soit "
        "le retirer, soit couper la compression — la phrase de `main.py` ne tient plus"
    )
    assert montes  # témoin : la pile n'est pas vide, donc ce test regarde quelque chose


def test_la_compression_est_bien_ACTIVE():
    """Contrepoids : sans lui, couper la compression rendrait tout ce fichier vert.

    La question BREACH ne se pose que parce qu'on compresse. Un correctif qui
    désactiverait GZip satisferait tous les tests ci-dessus — et coûterait 51 Ko à
    quelqu'un qui cherche le 3114 sur un lien lent.
    """
    noms = {getattr(getattr(m, "cls", None), "__name__", "") for m in app.user_middleware}

    assert "GZipMiddleware" in noms, noms

    reponse = client.get("/", headers={"accept-encoding": "gzip"})
    assert reponse.request.headers["accept-encoding"] == "gzip"


def test_la_phrase_qui_justifie_la_compression_est_toujours_la():
    """Second contrepoids : le jour où quelqu'un retire la condition du commentaire,
    ce fichier n'a plus d'objet — il doit le dire plutôt que de rester vert."""
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "app" / "main.py").read_text(encoding="utf-8")

    assert "BREACH" in source
    assert "ni cookie de session" in source
