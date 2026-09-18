# -*- coding: utf-8 -*-
"""« Bien sûr ! Voici 5 étapes : » n'est pas une micro-étape.

19/09/2026. `_lines` découpe la réponse du modèle en items, une ligne = un item. Les prompts
demandent « une étape par ligne, rien d'autre » — et la plupart des modèles répondent quand
même avec une phrase d'annonce, puis la liste.

Comportement **mesuré avant d'écrire ce fichier**, sur une réponse de modèle typique :

    items rendus : 5
      1. Bien sûr ! Voici 5 micro-étapes pour avancer :   <- du bavardage, place 1
      2. Ouvrir le document
      3. Écrire le titre
      4. Lister trois idées
      5. Rédiger le premier paragraphe
                                                          <- « Relire une fois » PERDUE

Deux dégâts pour la même cause : l'annonce occupe la première place, et la troncature à
`limit` fait tomber la dernière vraie étape.

**Pour qui.** `/focus/decompose` s'adresse à quelqu'un en paralysie exécutive, qui demande
qu'on casse une tâche en gestes faisables. Lui rendre une liste dont le premier élément n'est
pas une action, et à qui il manque la fin, c'est l'inverse exact de ce que l'écran promet —
et c'est précisément la personne qui n'ira pas re-demander.

Ce que le correctif n'est PAS : un nettoyage de politesse généralisé. Une seule forme est
écartée, celle qui est mesurée et sans ambiguïté — une ligne qui **annonce** la liste, donc
qui se termine par deux-points. Le reste du texte du modèle est rendu tel quel.
"""
from __future__ import annotations

from app.llm import _lines

REPONSE_BAVARDE = """Bien sûr ! Voici 5 micro-étapes pour avancer :
1. Ouvrir le document
2. Écrire le titre
3. Lister trois idées
4. Rédiger le premier paragraphe
5. Relire une fois"""


def test_une_ligne_qui_ANNONCE_la_liste_n_en_fait_pas_partie():
    items = _lines(REPONSE_BAVARDE, ["repli"], limit=5)

    assert not items[0].endswith(":"), (
        "la première micro-étape proposée à quelqu'un de bloqué ne peut pas être "
        f"une phrase d'introduction : {items[0]!r}"
    )
    assert "Bien sûr" not in items[0]


def test_la_DERNIERE_etape_n_est_plus_mangee_par_l_annonce():
    items = _lines(REPONSE_BAVARDE, ["repli"], limit=5)

    assert len(items) == 5
    assert items[-1] == "Relire une fois", (
        "l'annonce prenait une place, et la troncature faisait tomber la vraie dernière étape"
    )


def test_les_cinq_etapes_rendues_sont_les_cinq_VRAIES():
    assert _lines(REPONSE_BAVARDE, ["repli"], limit=5) == [
        "Ouvrir le document",
        "Écrire le titre",
        "Lister trois idées",
        "Rédiger le premier paragraphe",
        "Relire une fois",
    ]


def test_une_reponse_deja_propre_n_est_pas_touchee():
    """Le contrepoids : le correctif ne doit rien changer quand le modèle obéit."""
    propre = "Ouvrir le document\nÉcrire le titre\nRelire une fois"

    assert _lines(propre, ["repli"], limit=5) == [
        "Ouvrir le document", "Écrire le titre", "Relire une fois",
    ]


def test_une_reponse_QUE_d_annonces_retombe_sur_le_repli():
    """Si on jette tout, il faut rendre le repli — pas une liste vide.

    Sans cette ligne, l'écran afficherait zéro étape à quelqu'un qui en demandait cinq, ce
    qui est pire que le bavardage qu'on vient de retirer.
    """
    assert _lines("Voici :\nEt donc :", ["repli 1", "repli 2"], limit=2) == ["repli 1", "repli 2"]


def test_un_deux_points_AU_MILIEU_d_une_etape_ne_la_disqualifie_pas():
    """Second contrepoids : c'est la ligne qui *se termine* par deux-points qui annonce.

    « Ouvrir le fichier : celui de mardi » est une étape, pas une introduction.
    """
    texte = "Ouvrir le fichier : celui de mardi\nRelire une fois"

    assert _lines(texte, ["repli"], limit=2) == [
        "Ouvrir le fichier : celui de mardi", "Relire une fois",
    ]
