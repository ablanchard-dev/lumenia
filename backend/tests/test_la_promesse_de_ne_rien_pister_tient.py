# -*- coding: utf-8 -*-
"""« Aucun traceur, aucune mesure d'audience, aucun pixel publicitaire. »

18/09/2026. C'est la page de confidentialité qui le dit, au présent, sans
condition. La checklist d'Alex demande un outil d'analytics ; sur Lumenia la
réponse est **zéro**, et une réponse à zéro se garde comme une autre — sinon
elle n'est vraie que le jour où on l'a écrite.

Mesure du jour, sans défaut trouvé : aucune page ne charge quoi que ce soit
d'un domaine tiers, aucune réponse ne pose de cookie. La promesse était tenue
à la main. Un `<script src="https://…/analytics.js">` ajouté un soir la rendrait
fausse sans rien casser — c'est exactement le genre de ligne qu'on ajoute en
pensant bien faire, et sur une application de santé mentale c'est la liste des
pages consultées par quelqu'un en détresse qui part chez un tiers.

**Ce que le crible distingue.** Charger n'est pas lier. Un `<a href>` vers le
site du 3114 est un lien : la personne clique, ou non, et c'est elle qui décide.
Un `src` ou un `<link rel=stylesheet>` part **tout seul**, au chargement, et
transmet l'adresse IP et la page consultée sans que personne n'ait rien demandé.
Seul le second pisté. Un crible qui accuserait les liens sortants serait
désactivé la semaine suivante.

Le fichier garde aussi la phrase elle-même : une promesse qu'on efface est une
promesse qui ne rougit plus.
"""
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Ce qui part TOUT SEUL au chargement de la page, sans geste de la personne.
#
# Le `<link>` demande un tri. Un premier essai prenait tous les `href` et accusait
# les trois pages : il voyait `<link rel="canonical" href="http://localhost:8000/">`,
# qui ne télécharge rien — c'est une déclaration pour les moteurs de recherche.
# Trois accusations, trois faux positifs. Seuls ces `rel` déclenchent une requête.
CHARGE_AU_REL = r"(?:stylesheet|icon|preload|prefetch|preconnect|dns-prefetch|manifest|apple-touch-icon)"
CHARGEMENTS = re.compile(
    r"""<(?:script|img|iframe|video|audio|source|embed)\b[^>]*\bsrc\s*=\s*["']([^"']+)"""
    rf"""|<link\b(?=[^>]*\brel\s*=\s*["'][^"']*{CHARGE_AU_REL})[^>]*\bhref\s*=\s*["']([^"']+)""",
    re.IGNORECASE,
)


def _pages_publiques() -> list[str]:
    """Le sitemap comme source : une page ajoutée demain entre d'elle-même ici."""
    plan = client.get("/sitemap.xml")
    assert plan.status_code == 200
    return sorted({
        re.sub(r"^https?://[^/]+", "", url) or "/"
        for url in re.findall(r"<loc>([^<]+)</loc>", plan.text)
    })


def _chargements(page: str) -> list[str]:
    reponse = client.get(page)
    assert reponse.status_code == 200, page
    return [a or b for a, b in CHARGEMENTS.findall(reponse.text)]


def test_le_crible_voit_bien_des_chargements():
    """Témoin de contenu : sans lui, tout ce qui suit serait vert sur du vide."""
    tous = [c for page in _pages_publiques() for c in _chargements(page)]

    assert len(tous) >= 3, tous
    assert any(c.endswith("app.js") for c in tous), "le script de la page doit être vu"


def test_le_crible_distingue_un_chargement_d_un_lien_sortant():
    """Témoin inverse, sur la distinction qui fait tout le fichier."""
    assert CHARGEMENTS.search('<script src="https://t.exemple/a.js"></script>')
    assert CHARGEMENTS.search('<link rel="stylesheet" href="https://cdn.exemple/x.css">')
    assert not CHARGEMENTS.search('<a href="https://3114.fr">le 3114</a>'), (
        "un lien sortant ne part pas tout seul : c'est la personne qui décide"
    )
    assert not CHARGEMENTS.search('<link rel="canonical" href="https://lumenia.fr/">'), (
        "une URL canonique est une déclaration pour les moteurs, rien n'est téléchargé — "
        "c'est ce que le premier essai n'avait pas vu, et il accusait les trois pages"
    )


@pytest.mark.parametrize("page", _pages_publiques())
def test_aucune_page_ne_charge_quoi_que_ce_soit_d_un_tiers(page):
    tiers = [
        cible for cible in _chargements(page)
        if re.match(r"https?://|//", cible)
    ]

    assert tiers == [], (
        f"{page} charge {tiers} depuis un domaine tiers. Ce chargement part tout seul et "
        "transmet l'adresse IP et la page consultée : sur Lumenia, c'est la liste des pages "
        "lues par quelqu'un en détresse. La page de confidentialité promet le contraire"
    )


@pytest.mark.parametrize("page", _pages_publiques())
def test_aucune_reponse_ne_pose_de_cookie(page):
    """Mesuré sur la réponse réelle, pas sur une lecture des sources.

    Un cookie peut venir d'un middleware ou d'une dépendance sans qu'aucun
    `set_cookie` n'apparaisse dans le code de l'application.
    """
    reponse = client.get(page)

    assert "set-cookie" not in {k.lower() for k in reponse.headers}, (
        f"{page} dépose un cookie ; la page de confidentialité dit qu'aucun ne l'est, "
        "et c'est ce choix qui dispense Lumenia d'une bannière de consentement"
    )


def test_la_promesse_est_toujours_ecrite_noir_sur_blanc():
    """La garde d'en face : effacer la phrase suffirait à rendre tout le reste inutile.

    Un crible qui ne tient que des faits laisse partir la promesse qu'il gardait.
    """
    page = client.get("/confidentialite")
    assert page.status_code == 200

    for promesse in ("aucun traceur", "aucune mesure d'audience", "aucun pixel"):
        assert promesse in page.text.lower(), (
            f"la page de confidentialité ne promet plus « {promesse} ». Si c'est "
            "délibéré, les tests de ce fichier n'ont plus d'objet et doivent partir "
            "avec elle ; sinon, la phrase a été perdue dans une réécriture"
        )
