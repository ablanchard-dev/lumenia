# -*- coding: utf-8 -*-
"""Une page légale annonce sa date de mise à jour. Elle doit dire vrai.

18/09/2026. Les CGU et la politique de confidentialité portent toutes deux
« Dernière mise à jour : … ». C'est la seule chose qui permet à quelqu'un de
savoir si le texte qu'il lit est celui qu'il a accepté.

Mesure du jour : la politique de confidentialité affichait le 17 septembre alors
que son contenu avait changé le 18 — le paragraphe sur l'anti-spam et l'adresse
IP, ajouté le matin même. Le texte s'était mis à jour, sa date non.

Une date figée est pire qu'une date absente : elle affirme que rien n'a bougé.
Sur une page qui décrit ce qu'un serveur garde de vous, c'est exactement ce qu'on
ne peut pas laisser dire.

Le test compare la date affichée à la dernière modification réelle du fichier,
lue dans l'historique git — la seule source qui ne se met pas à jour toute seule
dans le bon sens.
"""
import re
import subprocess
from datetime import date
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
PAGES_LEGALES = ("confidentialite.html", "cgu.html")

MOIS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}


def _date_affichee(nom: str) -> date:
    texte = (RACINE / "static" / nom).read_text(encoding="utf-8")
    m = re.search(r"Derni[èe]re mise à jour\s*:\s*(\d{1,2})\s+([a-zéûôA-Z]+)\s+(\d{4})", texte)
    assert m, f"{nom} n'annonce plus sa date de mise à jour"
    jour, mois, annee = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    assert mois in MOIS, f"mois inconnu dans {nom} : {mois}"
    return date(annee, MOIS[mois], jour)


def _date_du_dernier_changement(nom: str) -> date | None:
    """La dernière date où le fichier a VRAIMENT changé, d'après git."""
    chemin = RACINE / "static" / nom
    try:
        sortie = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short", "--", str(chemin)],
            cwd=RACINE, capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    valeur = sortie.stdout.strip()
    if sortie.returncode != 0 or not valeur:
        return None
    return date.fromisoformat(valeur)


def test_le_crible_sait_lire_une_date_affichee():
    """Témoin : sans lui, un motif cassé rendrait les tests suivants muets."""
    for nom in PAGES_LEGALES:
        lue = _date_affichee(nom)
        assert lue.year >= 2025, (nom, lue)


@pytest.mark.parametrize("nom", PAGES_LEGALES)
def test_la_date_affichee_correspond_au_dernier_changement(nom):
    reelle = _date_du_dernier_changement(nom)
    if reelle is None:
        pytest.skip("hors d'un dépôt git : la date réelle n'est pas mesurable ici")

    affichee = _date_affichee(nom)

    assert affichee >= reelle, (
        f"{nom} annonce le {affichee} alors que son contenu a changé le {reelle}. "
        "Une date figée affirme que rien n'a bougé — sur une page légale, c'est faux, "
        "et c'est la seule chose qui permet de savoir si le texte lu est celui accepté"
    )


@pytest.mark.parametrize("nom", PAGES_LEGALES)
def test_la_date_affichee_n_est_pas_dans_le_futur(nom):
    """L'autre sens de l'erreur : une date d'avance ne vaut pas mieux qu'une date en retard."""
    assert _date_affichee(nom) <= date.today()
