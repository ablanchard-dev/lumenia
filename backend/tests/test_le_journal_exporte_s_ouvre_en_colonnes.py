# -*- coding: utf-8 -*-
"""Le journal exporté s'ouvre-t-il **en colonnes** chez la personne qui le reçoit ?

19/09/2026. Ce fichier est déjà pensé pour un tableur, et deux corrections le prouvent :
le **BOM** (sans lui, Excel lit le fichier dans le codage local et tout le journal d'une
personne francophone s'affiche en mojibake) et le préfixe d'apostrophe sur `= + - @` (sans
lui, une cellule devient une formule exécutée à l'ouverture, chez le psy ou le médecin).

Il restait la moitié la plus visible. Le séparateur est la **virgule** — le standard
RFC 4180 — mais Excel ne lit pas un CSV avec un séparateur fixe : il emploie le **séparateur
de liste de Windows**, qui vaut `;` en français, en allemand, en espagnol, en italien. Un
double-clic sur ce fichier, sur une machine française, met **toute la ligne dans une seule
cellule**. Le journal reste lisible… en bloc, dans la colonne A.

Or c'est exactement le scénario que le produit vise : la page de confidentialité promet la
portabilité, l'écran offre le lien, et le tiers qui ouvre le fichier est **la psychologue de
quelqu'un**, sur un poste Windows français.

Le correctif est la déclaration `sep=,` en première ligne : Excel la lit et applique la
virgule, quelle que soit sa locale. Le séparateur du fichier **ne change pas** — il reste la
virgule standard, et l'en-tête reste `id,title,content,created_at`.
"""
from __future__ import annotations

import csv
import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def journal_exporte():
    c = TestClient(app)
    c.post("/journal", json={"title": "Jour 1", "content": "Une phrase, avec une virgule."})
    c.post("/journal", json={"title": "Jour 2", "content": "Ligne A\nLigne B"})
    return c.get("/journal/export").content


def test_le_crible_recupere_bien_un_export(journal_exporte):
    """Témoin : sans lui, un export vide rendrait tout vert sans rien regarder."""
    assert len(journal_exporte) > 50
    assert b"Jour 1" in journal_exporte


def test_le_fichier_dit_a_EXCEL_quel_separateur_employer(journal_exporte):
    """Sans cette ligne, un double-clic sur une machine française met tout en colonne A."""
    texte = journal_exporte.decode("utf-8-sig")

    assert texte.splitlines()[0] == "sep=,", (
        "Excel n'emploie pas un séparateur fixe : il prend celui de Windows, qui vaut « ; » "
        "en français. La personne qui reçoit ce journal le verrait en une seule colonne"
    )


def test_le_BOM_reste_la_premiere_chose_du_fichier(journal_exporte):
    """Contrepoids : la déclaration ne doit pas passer DEVANT le BOM.

    Excel a besoin des deux, et dans cet ordre — le BOM annonce l'encodage, et il ne sert
    plus à rien s'il n'est pas au tout début.
    """
    assert journal_exporte.startswith(b"\xef\xbb\xbf")
    assert journal_exporte[3:].startswith(b"sep=,")


def test_le_fichier_reste_un_CSV_a_VIRGULES_et_se_relit(journal_exporte):
    """Le séparateur du fichier ne change pas : la déclaration ne fait que le nommer.

    On relit l'export avec le lecteur CSV standard, en sautant la déclaration : les colonnes
    et le contenu doivent être intacts, sauts de ligne internes compris.
    """
    texte = journal_exporte.decode("utf-8-sig")
    apres_declaration = texte.split("\n", 1)[1]

    lignes = list(csv.reader(io.StringIO(apres_declaration)))

    assert lignes[0] == ["id", "title", "content", "created_at"]

    # Premiere version : `lignes[1]`, `lignes[2]`. Vert seul, ROUGE en suite complete --
    # la base porte alors les entrees des autres tests et l'ordre change. Un test qui
    # depend de ce que la machine a vecu n'est pas un test unitaire (lecon du tour 116,
    # commise ici meme).
    par_titre = {l[1]: l[2] for l in lignes[1:] if len(l) >= 3}

    assert par_titre["Jour 1"] == "Une phrase, avec une virgule."
    assert par_titre["Jour 2"] == "Ligne A\nLigne B", \
        "un saut de ligne interne reste dans sa cellule"


def test_la_protection_contre_les_formules_tient_toujours(journal_exporte):
    """Second contrepoids : ce tour ne doit défaire aucune des deux corrections précédentes."""
    c = TestClient(app)
    c.post("/journal", json={"title": "=1+1", "content": "@rien"})

    texte = c.get("/journal/export").content.decode("utf-8-sig")

    assert "'=1+1" in texte, "une cellule qui commence par = reste du texte"
    assert "'@rien" in texte
