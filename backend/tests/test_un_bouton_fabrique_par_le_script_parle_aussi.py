# -*- coding: utf-8 -*-
"""Les boutons que le script fabrique ne sont dans aucune page.

19/09/2026. Le dépôt vérifie que les contrôles sans texte portent un nom : les quatre
boutons-icônes de `index.html` — menu, nouvelle conversation, fermer la bannière,
envoyer — sont tous nommés, et un crible le tient.

Ce crible lit le HTML **servi**. Or `app.js` fabrique trois boutons à l'exécution :
les choix d'une épreuve, l'ouverture d'une conversation, et sa suppression. Aucun
n'existe dans une page ; aucun n'est donc regardé, **par construction** — la même
forme de trou que la veille côté DrDXT, où un crible qui cherchait des `Foreground`
ne pouvait pas voir un fond de sélection.

MESURE, ET IL N'Y A PAS DE DÉFAUT : les trois parlent. Le bouton de choix reçoit le
texte de la réponse, celui d'ouverture le titre de la conversation, et celui de
suppression — dont tout le contenu est une corbeille dessinée — porte
`aria-label="Supprimer cette conversation"`.

CE QUE CE FICHIER TIENT. Le bouton de suppression est le seul du produit dont le sens
vit entièrement dans un dessin, et c'est aussi celui qui **détruit** quelque chose.
Sans son nom, une personne qui navigue au lecteur d'écran entend « bouton », à côté
d'un autre bouton qui, lui, s'annonce par le titre de la conversation. Le geste
irréversible serait le seul muet.
"""
from __future__ import annotations

import re
from pathlib import Path

APP_JS = (Path(__file__).resolve().parent.parent / "static" / "app.js").read_text(encoding="utf-8")

# Ce qui, dans le bloc de construction, donne un nom au bouton.
PAROLES = ("textContent", "innerText", "aria-label", "aria-labelledby")

# Assez de lignes pour couvrir une construction, pas assez pour déborder sur la suivante.
LIGNES_DU_BLOC = 12


def _boutons_fabriques() -> list[tuple[int, str, str]]:
    """(ligne, variable, bloc) pour chaque bouton créé par le script."""
    lignes = APP_JS.split("\n")
    trouves = []
    for m in re.finditer(r'createElement\("button"\)', APP_JS):
        n = APP_JS[: m.start()].count("\n")
        variable = re.search(r"(?:const|let|var)\s+(\w+)\s*=", lignes[n])
        trouves.append((n + 1, variable.group(1) if variable else "?",
                        "\n".join(lignes[n:n + LIGNES_DU_BLOC])))
    return trouves


def test_le_crible_trouve_bien_les_boutons_du_script():
    """Témoin : sans lui, un motif cassé rendrait tout le reste vert sur du vide."""
    boutons = _boutons_fabriques()

    assert len(boutons) >= 3, boutons
    assert any(v == "del" for _, v, _ in boutons), [v for _, v, _ in boutons]


def test_chaque_bouton_fabrique_dit_quelque_chose():
    muets = [
        f"app.js:{ligne} ({variable})"
        for ligne, variable, bloc in _boutons_fabriques()
        if not any(p in bloc for p in PAROLES)
    ]

    assert muets == [], (
        "ces boutons n'existent dans aucune page : le crible du HTML ne peut pas les "
        f"voir, et un lecteur d'écran annoncerait « bouton », sans plus — {muets}"
    )


def test_le_bouton_qui_SUPPRIME_porte_un_nom_explicite():
    """Le cas qui compte : tout son contenu est un dessin, et son geste est irréversible.

    Un `textContent` ne suffirait pas ici — il n'y en a pas, la corbeille est un SVG.
    Seul un `aria-label` peut parler à sa place.
    """
    bloc = next(b for _, v, b in _boutons_fabriques() if v == "del")

    assert "aria-label" in bloc, bloc
    assert "Supprimer" in bloc, "le nom doit dire ce que le geste fait"


def test_le_crible_reconnait_un_bouton_muet():
    """Témoin inverse : sans lui, un motif trop large rendrait tout vert.

    Le dépôt n'en contient aucun — c'est justement pour ça qu'il faut vérifier que le
    crible saurait en voir un.
    """
    faux = 'const x = document.createElement("button");\nx.className = "muet";\nparent.appendChild(x);'

    assert not any(p in faux for p in PAROLES)
