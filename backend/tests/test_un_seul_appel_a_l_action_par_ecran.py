# -*- coding: utf-8 -*-
"""Un écran qui propose deux fois « la » chose à faire n'en propose aucune.

Demande d'Alex, mot pour mot dans le registre de la boucle : « un seul CTA ». Lumenia est
une SPA : ses écrans vivent dans le même fichier et s'affichent l'un après l'autre. La règle
se lit donc **par écran**, pas par page — et rien ne la tenait.

L'enjeu n'est pas cosmétique ici. Le parcours d'entrée est déjà une charge cognitive : c'est
un test, il est éliminatoire, et il s'adresse à des personnes que deux boutons de même poids
mettent en arbitrage au lieu de les faire avancer. Le produit s'adresse explicitement à des
profils pour qui ce genre d'arbitrage coûte.

État mesuré à l'écriture : exactement un bouton principal par écran, sauf l'écran de
conversation — dont l'action est le bouton d'envoi de son formulaire. Aucun défaut ; ce qui
manquait, c'est ce qui empêche le second de s'ajouter demain.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[1] / "static" / "index.html"

# Les écrans de la SPA, dans l'ordre où le visiteur les rencontre.
ECRANS = ["screen-splash", "screen-consent", "screen-challenge", "screen-fail", "screen-chat"]

# L'écran de conversation n'a pas de bouton principal : son action est l'envoi du message,
# porté par le bouton de son formulaire. Ce n'est pas une dérogation de confort — le test du
# dessous exige que cet écran porte bien UNE action, juste écrite autrement.
SANS_BOUTON_PRINCIPAL = {"screen-chat"}


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def _blocs() -> dict[str, str]:
    """Le texte de chaque écran, découpé sur les positions des identifiants."""
    html = _html()
    positions = sorted(((html.index(f'id="{e}"'), e) for e in ECRANS))
    blocs = {}
    for i, (debut, nom) in enumerate(positions):
        fin = positions[i + 1][0] if i + 1 < len(positions) else len(html)
        blocs[nom] = html[debut:fin]
    return blocs


def _boutons_principaux(bloc: str) -> list[str]:
    return re.findall(r'<button[^>]*\bclass="[^"]*\bbtn-primary\b[^"]*"', bloc)


def test_le_crible_trouve_bien_les_ecrans_et_leurs_boutons():
    """Témoin : sans lui, un fichier réorganisé rendrait tout vert sur du vide."""
    blocs = _blocs()

    assert len(blocs) == len(ECRANS)
    assert all(len(b) > 200 for b in blocs.values()), "un écran vide ne prouve rien"
    assert sum(len(_boutons_principaux(b)) for b in blocs.values()) >= 4, (
        "le crible doit voir de vrais boutons principaux"
    )


@pytest.mark.parametrize("ecran", [e for e in ECRANS if e not in SANS_BOUTON_PRINCIPAL])
def test_chaque_ecran_ne_porte_qu_un_seul_bouton_principal(ecran):
    trouves = _boutons_principaux(_blocs()[ecran])

    assert len(trouves) == 1, (
        f"{ecran} porte {len(trouves)} boutons principaux. Deux actions de même poids sur "
        "un écran, c'est un arbitrage de plus à faire — et ce produit s'adresse à des "
        "personnes pour qui cet arbitrage coûte"
    )


def test_l_ecran_de_conversation_porte_bien_une_action_meme_sans_bouton_principal():
    """La dérogation doit être prouvée, pas déclarée : sinon elle devient une échappatoire."""
    bloc = _blocs()["screen-chat"]

    assert _boutons_principaux(bloc) == [], "l'écran de chat n'a pas de bouton principal"
    assert re.search(r'<button[^>]*type="submit"', bloc), (
        "mais il DOIT porter une action : l'envoi du message"
    )


def test_les_actions_secondaires_ne_se_deguisent_pas_en_principale():
    """Le contrepoids : les boutons secondaires existent et ne sont pas comptés.

    Sans lui, on aurait pu satisfaire la règle en retirant la classe à tout le monde.
    """
    html = _html()

    for classe in ("btn-secondary", "btn-ghost", "btn-icon"):
        assert re.search(rf'class="[^"]*\b{classe}\b', html), (
            f"{classe} doit exister : la hiérarchie visuelle est ce qui rend le CTA unique"
        )
