# -*- coding: utf-8 -*-
"""« Refusé aux robots » ne se dit pas dans robots.txt — c'est même le contraire.

19/09/2026. `test_rien_de_servi_n_est_orphelin.py` se termine sur cette phrase :
« il exige que chaque page servie soit soit un écran du produit, soit un atelier
**déclaré** — et, dans ce cas, **refusé aux robots**. » Trois planches de travail
internes sont dans ce cas : `logo-lab.html`, `intro-preview.html`, `og-card.html`.

Le refus est implémenté par une ligne `Disallow:` dans `robots.txt`. Et
`Disallow` ne fait pas ce que la phrase promet.

CE QUE `Disallow` FAIT VRAIMENT. Il interdit l'**exploration**, pas
l'**indexation**. Google le documente en toutes lettres : une URL bloquée par
robots.txt peut apparaître dans les résultats si elle est liée depuis ailleurs —
sans description, mais avec son adresse. Sur une application de santé mentale,
l'adresse `…/static/logo-lab.html` à côté du vrai site, c'est exactement ce que
le fichier d'origine disait vouloir éviter.

ET LE PIÈGE SE REFERME. La seule directive qui empêche vraiment l'indexation est
`noindex` — balise ou en-tête. Or, même documentation : « pour que la règle
noindex soit effective, la page ne doit pas être bloquée par un fichier
robots.txt, et doit rester accessible au robot. » Un moteur qui n'a pas le droit
de lire la page ne lira jamais son `noindex`. **Les deux mécanismes se
neutralisent**, et le dépôt n'avait que le mauvais des deux.

Les pages 404 et 500, elles, portent bien `<meta name="robots" content="noindex">` —
la bonne directive, au bon endroit. La règle était donc écrite quelque part, et
pas appliquée là où elle comptait le plus. Une surface, une promesse, deux
mécanismes, et seul celui qui ne marche pas était en place.

CORRECTIF : l'en-tête `X-Robots-Tag: noindex` sur les pages d'atelier — il vaut
pour tous les formats, y compris ceux qui n'ont pas de `<head>` — et le retrait
de leur `Disallow`, sans quoi l'en-tête ne serait jamais lu.

⚠️ LE CONTREPOIDS COMPTE AUTANT. Un `noindex` qui déborderait sur une page du
produit la ferait DISPARAÎTRE des moteurs. C'est la panne la plus coûteuse
possible pour un site qui cherche à être trouvé, et elle est silencieuse.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ATELIERS = ("logo-lab.html", "intro-preview.html", "og-card.html")
ECRANS = ("/", "/cgu", "/confidentialite")


def test_le_crible_atteint_bien_les_planches_internes():
    """Témoin : si ces pages cessaient d'être servies, tout le reste serait vert sur du vide."""
    for nom in ATELIERS:
        r = client.get(f"/static/{nom}")
        assert r.status_code == 200, (nom, r.status_code)
        assert len(r.content) > 500, nom


def test_chaque_planche_interne_porte_un_vrai_refus_d_indexation():
    for nom in ATELIERS:
        entete = client.get(f"/static/{nom}").headers.get("x-robots-tag", "")

        assert "noindex" in entete.lower(), (
            f"/static/{nom} n'est refusé aux robots que par un `Disallow`, qui empêche de "
            "l'explorer sans empêcher d'indexer son adresse"
        )


def test_le_refus_reste_lisible_par_un_robot():
    """Le piège : un `Disallow` interdirait au moteur de lire ce `noindex`."""
    robots = client.get("/robots.txt").text

    for nom in ATELIERS:
        assert f"Disallow: /static/{nom}" not in robots, (
            f"{nom} porte un en-tête noindex ET un Disallow : les deux se neutralisent, "
            "un robot qui n'a pas le droit de lire la page ne verra jamais son noindex"
        )


def test_l_API_reste_interdite_d_exploration():
    """Contrepoids : retirer des Disallow ne doit pas ouvrir l'API aux moteurs.

    Une réponse JSON indexée est une fuite tranquille, et l'API n'a aucune page à
    montrer — là, `Disallow` est exactement le bon outil.
    """
    robots = client.get("/robots.txt").text

    assert "Disallow: /journal" in robots, robots
    assert "Disallow: /chat" in robots, robots


def test_aucune_page_du_PRODUIT_ne_se_retire_des_moteurs():
    """Le contrepoids qui compte : un noindex qui déborde fait disparaître le site.

    🔴 PREMIÈRE VERSION, ET ELLE NE POUVAIT PAS ÉCHOUER. Elle interrogeait `/`, `/cgu`
    et `/confidentialite` — des routes que le middleware statique ne touche jamais.
    Mutation appliquée : retirer la condition qui épargne les écrans du produit. Le
    test est resté **vert**. Il nommait une garantie sans la tenir.

    Ce que ce filtre garde réellement, c'est la REDIRECTION : `/static/index.html`
    répond 308 vers `/`, et cette réponse-là passe bien par le middleware statique.
    Un `noindex` posé sur la redirection d'une page du produit est exactement le
    débordement qu'on veut interdire — et il est observable.
    """
    for fichier in ("index.html", "cgu.html", "confidentialite.html", "404.html"):
        r = client.get(f"/static/{fichier}", follow_redirects=False)

        assert r.status_code in (301, 307, 308), (fichier, r.status_code)
        assert "noindex" not in r.headers.get("x-robots-tag", "").lower(), (
            f"/static/{fichier} redirige vers une page du PRODUIT : un noindex sur cette "
            "réponse est un refus d'indexation posé sur le chemin du vrai site"
        )

    # Et les routes canoniques, elles, ne portent aucun refus — ni en-tête, ni balise.
    for chemin in ECRANS:
        r = client.get(chemin)

        assert "noindex" not in r.headers.get("x-robots-tag", "").lower(), chemin
        assert 'content="noindex' not in r.text, chemin
