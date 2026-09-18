# -*- coding: utf-8 -*-
"""Chaque page a une adresse. Elle en avait deux, et la seconde était cassée.

18/09/2026. Les écrans du produit sont des **gabarits** : ils portent `{{ORIGIN}}`
dans `<link rel="canonical">`, `og:url` et `og:image`, et `web.page()` remplace ce
jeton par l'origine publique au moment de servir. C'est la bonne façon de faire —
un fichier statique ne peut pas connaître son adresse publique.

Mais ces gabarits vivent dans le dossier monté par `StaticFiles`. Mesure du jour :

    GET /            200  text/html   {{ORIGIN}} remplacé
    GET /static/index.html   200  text/html   {{ORIGIN}} **tel quel**
    GET /cgu         200  text/html   {{ORIGIN}} remplacé
    GET /static/cgu.html     200  text/html   {{ORIGIN}} **tel quel**

Donc chaque page existe à deux adresses, et la copie porte un `canonical` qui
n'est pas une URL (`{{ORIGIN}}/`) et une `og:image` introuvable. `robots.txt` ne
disait rien de ces deux chemins — il ne refusait que les trois planches de
travail. Un moteur pouvait indexer le double au lieu de l'original, et le double
ne pointait vers rien.

`/static/404.html` est le même piège d'un cran pire : 200 sur une page qui dit
« introuvable ». C'est le soft 404 du manuel.

Le correctif n'enlève rien du dossier : il donne une réponse à la seconde adresse
au lieu de la laisser servir le gabarit — une redirection permanente vers la vraie.
Les planches de travail, elles, restent servies (elles sont déclarées, et
`robots.txt` les refuse déjà).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# fichier servi -> la seule adresse qui doit rester
ECRANS = {
    "index.html": "/",
    "cgu.html": "/cgu",
    "confidentialite.html": "/confidentialite",
    "404.html": "/",
    "500.html": "/",
}

ATELIERS = ["logo-lab.html", "intro-preview.html", "og-card.html"]


def test_le_crible_lit_bien_une_page_gabarit():
    """Témoin : si les pages cessaient d'être des gabarits, tout le reste serait vert sur du vide."""
    rendue = client.get("/")

    assert rendue.status_code == 200
    assert "{{ORIGIN}}" not in rendue.text, "la route publique doit remplacer le jeton"
    assert 'rel="canonical"' in rendue.text


@pytest.mark.parametrize("fichier,canonique", sorted(ECRANS.items()))
def test_un_ecran_n_est_pas_servi_une_seconde_fois_sous_static(fichier, canonique):
    r = client.get(f"/static/{fichier}", follow_redirects=False)

    assert r.status_code in (301, 308), (
        f"/static/{fichier} repond {r.status_code} : la page existe a deux adresses. "
        f"La seconde sert le gabarit BRUT — son `canonical` vaut litteralement `{{{{ORIGIN}}}}/` "
        "et son `og:image` est introuvable. Un moteur peut indexer le double au lieu de l'original"
    )
    assert r.headers["location"] == canonique


@pytest.mark.parametrize("fichier", sorted(ECRANS))
def test_aucun_gabarit_brut_ne_sort_jamais(fichier):
    """La garantie qui compte vraiment : quel que soit le code, le jeton ne sort pas."""
    r = client.get(f"/static/{fichier}")  # redirections suivies

    assert "{{ORIGIN}}" not in r.text, (
        f"/static/{fichier} laisse echapper le jeton de gabarit : ce qui sort n'est pas une page, "
        "c'est un fichier source"
    )


@pytest.mark.parametrize("nom", ATELIERS)
def test_les_planches_declarees_restent_servies(nom):
    """L'autre sens : le correctif ne doit pas fermer le dossier statique."""
    assert client.get(f"/static/{nom}").status_code == 200
    assert client.get("/static/style.css").status_code == 200
