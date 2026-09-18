# -*- coding: utf-8 -*-
"""Une borne inférieure trop basse dit quelque chose de faux.

18/09/2026. Le README annonce « **70+** parametrized cases ». Mesure du jour :
**222 fonctions de test déclarées**, **374 cas exécutés**. « 70+ » n'est pas un
mensonge — 374 est bien supérieur à 70 — et c'est exactement ce qui le rend
difficile à voir : aucun test ne peut le déclarer faux.

Il dit pourtant quelque chose de faux. Un lecteur qui lit « 70+ » sur un dépôt
public se fait une idée de l'effort, et cette idée est cinq fois trop petite. La
phrase précise même que « the exact count is whatever pytest reports » : la forme
est honnête, c'est le nombre qui a vieilli sur place pendant que la suite
quintuplait.

**Ce que ce crible ne fait pas** : exiger le chiffre exact. Une borne qu'il faut
remonter à chaque test ajouté serait une borne qu'on finit par ne plus remonter,
et un test qui rougit pour ça serait désactivé. Il refuse seulement les bornes
**absurdes** — moins de la moitié de ce que le dépôt déclare.

On compte les `def test_`, pas les cas exécutés : c'est une minoration sûre (le
paramétrage ne fait qu'ajouter), et ça évite de lancer pytest depuis pytest.
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
README = BACKEND.parent / "README.md"

# `\s` couvre le saut de ligne : la phrase du README est coupee en deux, et c'est normal.
MOTIF = r"\*\*(\d+)\s+test\s+functions\*\*"


def _fonctions_de_test() -> int:
    return sum(
        len(re.findall(r"^def test_", f.read_text(encoding="utf-8-sig"), re.M))
        for f in sorted((BACKEND / "tests").glob("test_*.py"))
    )


def _fonctions_annoncees() -> int | None:
    """Le « from N test functions » du README : un nombre EXACT, donc tenable exactement.

    18/09/2026, deuxième passage sur la même phrase. La borne « N+ » ci-dessous est
    gardée depuis ce matin, mais la phrase porte aussi deux nombres exacts et datés —
    « **378 passing on 18/09/2026**, from 226 test functions » — que rien ne tenait.
    Mesure du jour : **441 collectés, 270 fonctions**. Les deux étaient faux le jour
    même de leur date, exactement comme le README de l'autre dépôt (tour 102).

    Un nombre exact n'a pas besoin d'une bande de tolérance : il se compte. Celui-ci
    se compte **sans lancer pytest depuis pytest**, ce qui est précisément pourquoi
    c'est lui qu'on garde, et pourquoi le nombre de cas exécutés, lui, reste décrit
    plutôt que chiffré — « whatever pytest reports », et la phrase le dit déjà.
    """
    # ⚠️ Le chiffre est cherché **en gras**, et ce n'est pas cosmétique. Première version :
    # `from\s+(\d+)\s+test\s+functions`, qui a attrapé la citation historique du paragraphe
    # (« "378 passing, from 226 test functions" were already stale ») au lieu de l'annonce
    # vivante — le crible lisait l'exemple périmé que la phrase donne pour expliquer le
    # piège, et rougissait sur lui. Un document qui se cite lui-même piège son propre crible.
    trouve = re.search(MOTIF, README.read_text(encoding="utf-8-sig"))
    return int(trouve.group(1)) if trouve else None


def _borne_annoncee() -> int | None:
    """Le « N+ » que le README met en avant pour la suite de tests."""
    trouve = re.search(r"(\d+)\+\s*(?:parametrized\s+)?cases", README.read_text(encoding="utf-8-sig"))
    return int(trouve.group(1)) if trouve else None


def test_le_crible_voit_bien_les_deux_nombres():
    """Témoin de contenu : sans lui, un README réécrit rendrait le garde muet."""
    assert _fonctions_de_test() > 50, "le crible ne lit pas les tests du dépôt"
    assert _borne_annoncee() is not None, "le README doit annoncer une taille de suite"


def test_l_extracteur_lit_une_borne_et_pas_n_importe_quel_nombre():
    """Témoin inverse : un extracteur qui rend toujours None passerait tout."""
    assert re.search(r"(\d+)\+\s*(?:parametrized\s+)?cases", "370+ parametrized cases").group(1) == "370"
    assert re.search(r"(\d+)\+\s*(?:parametrized\s+)?cases", "12+ cases").group(1) == "12"
    assert not re.search(r"(\d+)\+\s*(?:parametrized\s+)?cases", "Python 3.11 and 300 questions")


def test_la_taille_annoncee_n_est_pas_absurdement_basse():
    declarees = _fonctions_de_test()
    annoncee = _borne_annoncee()

    assert annoncee * 2 >= declarees, (
        f"le README annonce « {annoncee}+ » alors que le dépôt déclare {declarees} fonctions "
        f"de test (et en exécute davantage, paramétrage compris). La phrase n'est pas fausse, "
        "et c'est ce qui la rend invisible : elle donne au lecteur une idée de l'effort qui "
        "est plusieurs fois trop petite"
    )


def test_l_extracteur_de_fonctions_lit_bien_la_phrase():
    """Témoin inverse : un extracteur toujours None laisserait tout passer."""
    assert re.search(MOTIF, "…, from **270 test functions**.").group(1) == "270"
    coupee = "from **270 test" + chr(10) + "functions**"
    assert re.search(MOTIF, coupee).group(1) == "270", "la phrase du README est coupee en deux lignes"
    assert not re.search(MOTIF, "270 questions from the bank")
    # Le piege mesure : la citation historique du README, non grasse, ne doit pas repondre.
    assert not re.search(MOTIF, '("378 passing, from 226 test functions") were already stale')


def test_le_nombre_de_fonctions_annonce_est_le_vrai():
    declarees = _fonctions_de_test()
    annoncees = _fonctions_annoncees()

    assert annoncees is not None, "le README doit annoncer combien de fonctions de test existent"
    assert annoncees == declarees, (
        f"le README annonce {annoncees} fonctions de test, le dépôt en déclare {declarees}. "
        "Celui-là est exact et se compte : il n'a pas droit à une bande de tolérance. "
        "Le jour où quelqu'un ajoute un test, ce crible rougit et la phrase se met à jour "
        "dans le même commit — c'est tout ce qu'on lui demande"
    )
