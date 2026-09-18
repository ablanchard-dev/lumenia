# -*- coding: utf-8 -*-
"""Une page qui répond en GET doit répondre en HEAD.

Mesuré le 18/09/2026 en sondant les liens du site servi. Aucun lien n'est cassé —
mais **toutes** les pages renvoyaient `405 Method Not Allowed` sur `HEAD`, y compris
`/robots.txt`, `/sitemap.xml` et `/favicon.ico`.

Ce n'est pas un détail de protocole :
  • les moniteurs de disponibilité sondent en HEAD par défaut — le site serait
    rapporté en panne alors qu'il répond ;
  • les vérificateurs de liens (dont ceux des sites qui pointeraient vers Lumenia)
    sondent en HEAD — le lien serait compté mort ;
  • RFC 9110 §9.3.2 : HEAD est exigé de toute ressource qui accepte GET.

La cause tient au cadre, pas aux pages : `@app.get(...)` n'enregistre que GET.
Corrigé une fois pour toutes, à l'entrée, plutôt que route par route — une page
ajoutée demain est couverte sans qu'on y pense.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
NAVIGATEUR = {"accept": "text/html,application/xhtml+xml"}

CHEMINS = ["/", "/cgu", "/confidentialite", "/robots.txt", "/sitemap.xml", "/favicon.ico"]


@pytest.mark.parametrize("chemin", CHEMINS)
def test_head_repond_comme_get(chemin):
    get = client.get(chemin, headers=NAVIGATEUR)
    # Témoin : si GET lui-même ne servait rien, le test ci-dessous serait vide de sens.
    assert get.status_code == 200 and get.content, f"{chemin} ne répond déjà pas en GET"

    head = client.head(chemin, headers=NAVIGATEUR)
    assert head.status_code == 200, f"HEAD {chemin} → {head.status_code}"
    assert head.headers.get("content-type") == get.headers.get("content-type"), chemin
    # Pas d'assertion sur le corps ici, et c'est délibéré : le client HTTP jette
    # lui-même le corps d'une réponse à un HEAD. `head.content == b""` passait donc
    # même en supprimant le code qui vide la réponse — une assertion qui ne mord pas,
    # donc pire qu'absente. Mesuré autrement, au niveau socket contre le serveur
    # lancé (18/09/2026) : HEAD / → 200, **0 octet**, HSTS présent ; GET / → 17 420
    # octets. C'est cette mesure qui prouve le corps vide, pas ce test.


def test_head_garde_les_en_tetes_de_securite():
    """Sinon un sondage HEAD verrait un site sans HSTS ni CSP, et les en-têtes
    seraient « vrais » seulement pour qui demande la page entière."""
    head = client.head("/", headers=NAVIGATEUR)
    for entete in ("strict-transport-security", "content-security-policy",
                   "x-content-type-options", "referrer-policy"):
        assert entete in head.headers, f"{entete} absent de la réponse HEAD"


def test_une_methode_vraiment_absente_reste_refusee():
    """Le témoin inverse : ouvrir HEAD ne doit pas ouvrir tout le reste."""
    assert client.request("DELETE", "/").status_code in (405, 404)


# -----------------------------------------------------------------------------
# 18/09/2026 — constate en direct, pas deduit : apres avoir corrige `app.js`, le
# navigateur a continue d'executer l'ANCIEN script malgre un rechargement complet.
# Le fichier servi etait bon ; la page, elle, tournait sur une version perimee.
#
# Cause : les fichiers statiques ne portaient **aucun `cache-control`**. Sans
# directive, le navigateur applique une heuristique de fraicheur : le comportement
# depend du navigateur, et une mise a jour peut mettre longtemps a atteindre
# quelqu'un qui a deja ouvert le site.
#
# Les URL ne sont pas versionnees (`/static/app.js`, sans empreinte), donc la seule
# reponse sure est d'exiger une revalidation : `no-cache` ne veut pas dire « ne pas
# mettre en cache » mais « demande-moi avant de reutiliser ». Avec l'ETag deja
# present, la revalidation coute un 304 vide.
# -----------------------------------------------------------------------------

STATIQUES = ["/static/app.js", "/static/style.css", "/static/logo-mark.svg"]


@pytest.mark.parametrize("chemin", STATIQUES)
def test_les_fichiers_statiques_exigent_une_revalidation(chemin):
    reponse = client.get(chemin)
    assert reponse.status_code == 200, chemin
    cache = reponse.headers.get("cache-control", "")
    assert cache, f"{chemin} ne dit rien sur son cache : le navigateur decidera seul"
    assert "no-cache" in cache or "max-age=0" in cache, cache


@pytest.mark.parametrize("chemin", STATIQUES)
def test_l_empreinte_reste_la_pour_que_la_revalidation_soit_gratuite(chemin):
    """Temoin : exiger la revalidation sans ETag transformerait chaque visite en
    retelechargement complet — on aurait remplace un defaut par un autre."""
    reponse = client.get(chemin)
    assert reponse.headers.get("etag") or reponse.headers.get("last-modified"), chemin
