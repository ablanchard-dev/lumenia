# -*- coding: utf-8 -*-
"""Chaque tiers qui peut recevoir un message doit être nommé au client.

18/09/2026. Lumenia envoie le message courant et les tours récents à un modèle
exploité par un tiers. Le RGPD appelle ça un destinataire, et un destinataire se
déclare — avec son pays, parce qu'un transfert hors Union européenne n'est pas
la même chose qu'un hébergement en France.

Mesure du jour : les quatre fournisseurs du code sont bien nommés, sur l'accueil
et sur la page de confidentialité, chacun avec son pays. C'est juste, et rien ne
le tenait : ajouter une clé dans `_PROVIDERS` suffit à créer un cinquième
destinataire, et il partirait sans un mot.

Le crible lit les fournisseurs dans le code et exige que chacun soit nommé là où
le client peut le lire. Il exige aussi le pays : sans lui, la liste informe sur
le nom de l'entreprise et tait ce qui compte juridiquement.
"""
import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
PAGES = ("index.html", "confidentialite.html")

# Un pays reconnu : ce qui suit le nom du fournisseur sur la page.
PAYS = re.compile(r"(États-Unis|France|Union européenne|Royaume-Uni|Canada|Allemagne)", re.I)


def _fournisseurs_du_code() -> set[str]:
    """Les clés de `_PROVIDERS`, lues sur le module réel plutôt que dans le texte."""
    from app.llm import _PROVIDERS

    return set(_PROVIDERS)


def _page(nom: str) -> str:
    return (RACINE / "static" / nom).read_text(encoding="utf-8")


def test_le_crible_voit_bien_les_fournisseurs():
    """Témoin : un crible vide rendrait tout le reste vert sur le néant."""
    fournisseurs = _fournisseurs_du_code()

    assert len(fournisseurs) >= 2, fournisseurs
    assert "gemini" in fournisseurs


@pytest.mark.parametrize("page", PAGES)
def test_chaque_fournisseur_est_nomme_sur_la_page(page):
    texte = _page(page).lower()

    tus = sorted(f for f in _fournisseurs_du_code() if f.lower() not in texte)

    assert tus == [], (
        f"ces fournisseurs peuvent recevoir un message et ne sont pas nommés dans {page} : "
        f"{tus}. Un destinataire non déclaré, c'est une donnée de santé qui part chez "
        "quelqu'un dont le client n'a jamais entendu parler"
    )


def test_la_page_de_confidentialite_donne_le_pays_de_chaque_fournisseur():
    """Le nom seul ne dit pas l'essentiel : hors Union européenne ou non."""
    texte = _page("confidentialite.html")

    # Une ligne à la fois, repérée par son <strong> : chercher le nom n'importe où
    # dans la page attrapait un paragraphe voisin, et le test restait vert quand on
    # retirait le pays (vérifié par mutation). L'instrument avant la conclusion.
    lignes = {
        m.group(1).lower(): m.group(0)
        for m in re.finditer(r"<li><strong>([a-z]+)</strong>(.*?)</li>", texte, re.I | re.S)
    }

    sans_pays = [
        f for f in sorted(_fournisseurs_du_code())
        if f.lower() not in lignes or not PAYS.search(lignes[f.lower()])
    ]

    assert sans_pays == [], (
        f"ces fournisseurs sont nommés sans leur pays : {sans_pays}. Un transfert hors "
        "Union européenne ne se lit pas dans un nom d'entreprise"
    )


def test_la_page_ne_nomme_aucun_fournisseur_retire_du_code():
    """L'autre sens : une page qui annonce un tiers auquel plus rien n'est envoyé."""
    texte = _page("confidentialite.html")
    reels = {f.lower() for f in _fournisseurs_du_code()}

    cites = {m.lower() for m in re.findall(r"<li><strong>([a-z]+)</strong>", texte, re.I)}
    fantomes = sorted(c for c in cites if c not in reels)

    assert fantomes == [], f"la page annonce des destinataires que le code ne connaît pas : {fantomes}"
