# -*- coding: utf-8 -*-
"""Ce que le README dit d'un dossier doit correspondre à ce que le dépôt en fait.

18/09/2026, suite du tour 68. Le README dit :

    The `frontend/` folder is the old Streamlit interface, kept for reference but
    no longer used: the current UI lives in `backend/static/`...

Le dépôt dit autre chose. `docker-compose.yml` construit et lance ce dossier, et
`run_frontend.bat` comme `setup_windows_frontend.ps1` l'attendent à la racine,
prêts pour un double-clic. « Plus utilisé » est faux depuis un moment, et c'est
la phrase qui a fait que personne n'a regardé cette interface — jusqu'à ce qu'on
y trouve, au tour 68, un 3114 affiché sous condition.

C'est le coût réel d'une phrase périmée : elle ne se contente pas d'être fausse,
elle **dispense de regarder**.

Le crible ne tranche rien de ce qui doit rester : il est **bidirectionnel**. Un
dossier que le compose construit ne peut pas être annoncé mort dans le README ;
et le jour où Alex retirera ce service, le README devra cesser de dire qu'il
tourne. Les deux sens redeviennent faux à la première dérive.
"""
import re
from pathlib import Path

import pytest

DEPOT = Path(__file__).resolve().parent.parent.parent
MORT = re.compile(r"no longer used|kept for reference|n[' ]est plus utilis", re.I)


def _dossiers_construits() -> list[str]:
    """Les dossiers que `docker compose` construit vraiment."""
    compose = (DEPOT / "docker-compose.yml").read_text(encoding="utf-8-sig")
    return sorted({c.strip("./") for c in re.findall(r"^\s*build:\s*(\S+)", compose, re.M)})


def _passage_sur(dossier: str) -> str | None:
    """Le PARAGRAPHE du README qui parle de ce dossier, s'il y en a un.

    Premier essai : la seule phrase qui nomme le dossier. Il ne mordait pas.
    Remettre « no longer used » dans la phrase SUIVANTE laissait le crible vert,
    parce que le nom du dossier était resté dans la première. Le test nommait
    la garantie sans la tenir. Une affirmation sur un dossier vit dans son
    paragraphe, pas dans la phrase exacte qui le cite.
    """
    readme = (DEPOT / "README.md").read_text(encoding="utf-8-sig")
    # 🔴 Corrigé le 18/09/2026. Cette recherche exigeait le jeton EXACT `backend/`
    # ou `backend`. Le README ne l'écrit jamais ainsi : il dit `backend/static/`,
    # `backend/tests/`, `backend/data/lumenia.db`. Résultat, le cas `backend` se
    # SAUTAIT tout seul, avec un message qui affirmait le contraire de la réalité
    # — « le README ne dit rien de backend/ » — et la moitié de la garantie
    # annoncée par ce fichier n'était jamais vérifiée. Un test qui se désactive
    # lui-même ne rougit jamais : il ne peut pas.
    passages = _passages_sur(dossier)
    return passages[0] if passages else None


def _passages_sur(dossier: str) -> list[str]:
    """TOUS les paragraphes qui parlent de ce dossier, pas seulement le premier.

    🔴 Deuxième correction du 18/09/2026, trouvée parce qu'une mutation n'a pas
    mordu : déclarer `backend/` « no longer used » laissait la suite verte. La
    recherche s'arrêtait au PREMIER paragraphe citant le dossier — pour
    `backend`, le paragraphe des prérequis — et la phrase mortelle vivait trois
    paragraphes plus bas. Même faute que celle décrite plus haut, d'un cran plus
    large : phrase → paragraphe → *tous* les paragraphes.

    Bruyance mesurée avant d'élargir : 4 paragraphes pour `backend`, 1 pour
    `frontend`, aucun mot d'enterrement dans aucun. Zéro accusation nouvelle.
    """
    readme = (DEPOT / "README.md").read_text(encoding="utf-8-sig")
    # Le jeton doit accepter un CHEMIN : le README écrit `backend/static/`,
    # `backend/tests/`, jamais `backend/` tout court. Exiger la forme nue faisait
    # que le cas `backend` se sautait lui-même, avec un message qui affirmait le
    # contraire de la réalité. Un test qui se désactive ne rougit jamais.
    cite = re.compile(r"`" + re.escape(dossier) + r"(?:/[^`]*)?`")
    return [p for p in (" ".join(b.split()) for b in re.split(r"\n\s*\n", readme)) if cite.search(p)]


def test_le_crible_voit_bien_les_deux_cotes():
    """Témoin de contenu : sans lui, un fichier déplacé rendrait le garde muet."""
    construits = _dossiers_construits()

    assert construits == ["backend", "frontend"], construits
    assert _passage_sur("frontend"), "le README doit bien parler de ce dossier"


@pytest.mark.parametrize("dossier", _dossiers_construits())
def test_aucun_dossier_construit_ne_s_echappe_du_crible(dossier):
    """Le garde ne doit pas pouvoir se taire sur un dossier.

    18/09/2026 : il le pouvait. `test_un_dossier_..._n_est_pas_annonce_mort`
    s'autorise un `skip` quand le README ne parle pas du dossier — une porte de
    sortie légitime en principe. En pratique elle s'ouvrait pour `backend`, que
    le README cite pourtant à chaque section, parce que la recherche exigeait le
    jeton exact `backend/`. Le message du skip affirmait alors quelque chose de
    faux sur le README, et personne ne lit un skip.

    Ce test-ci refuse le silence : si un dossier construit n'a aucun passage, ce
    doit être un fait vérifié, pas un défaut de recherche.
    """
    assert _passage_sur(dossier), (
        f"aucun paragraphe du README ne cite {dossier}/ — soit c'est vrai et le README a un "
        "trou, soit la recherche est trop stricte et le garde se saute lui-meme en silence"
    )


def test_le_detecteur_reconnait_une_phrase_qui_enterre_un_dossier():
    """Témoin inverse : un détecteur qui ne mord jamais rendrait tout vert."""
    assert MORT.search("kept for reference but no longer used")
    assert MORT.search("ce dossier n'est plus utilisé")
    assert not MORT.search("the current UI lives in backend/static and is served")


@pytest.mark.parametrize("dossier", _dossiers_construits())
def test_un_dossier_que_le_compose_lance_n_est_pas_annonce_mort(dossier):
    passages = _passages_sur(dossier)
    if not passages:
        pytest.skip(f"le README ne dit rien de {dossier}/ : rien à contredire")

    enterrement = next((p for p in passages if MORT.search(p)), None)

    assert enterrement is None, (
        f"le README annonce {dossier}/ hors service — « {enterrement} » — mais "
        "docker-compose.yml le construit et le lance. Une phrase périmée ne se contente "
        "pas d'être fausse : elle dispense de regarder, et c'est comme ça qu'un 3114 "
        "affiché sous condition a tenu 33 tours sans être vu"
    )


def test_ce_que_le_readme_annonce_lance_l_est_vraiment():
    """L'autre sens : le jour où le service disparaît du compose, la phrase doit suivre."""
    passage = _passage_sur("frontend")
    assert passage, "témoin : le README parle bien de ce dossier"

    if "frontend" not in _dossiers_construits():
        assert MORT.search(passage), (
            "le compose ne construit plus frontend/, mais le README le décrit toujours "
            "comme une interface vivante"
        )
