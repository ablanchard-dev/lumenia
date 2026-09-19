# -*- coding: utf-8 -*-
"""Les deux cribles de contraste lisent des tokens. Trois fonds n'en sont pas.

19/09/2026. Le dépôt mesure le contraste de deux façons, et les deux sont bonnes :
`test_aucune_encre_ne_passe_sous_le_seuil` relit chaque encre **tokenisée** face aux
fonds sur lesquels elle est posée, et `test_une_encre_ecrite_en_dur_n_echappe_pas_au_crible`
attrape celles qui n'ont pas de nom. Ensemble, elles couvrent toutes les ENCRES.

Aucune des deux ne sait composer un FOND. Trois règles en emploient un :

    .choice.selected  background: color-mix(in srgb, var(--primary) 12%, var(--surface-2))
    .choice.correct   background: color-mix(in srgb, var(--accent)  13%, var(--surface-2))
    .choice.wrong     background: color-mix(in srgb, var(--danger)  11%, var(--surface-2))

Ce ne sont ni `--surface-2` ni `--primary` : ce sont trois couleurs qui n'existent
nulle part dans la feuille, calculées par le navigateur. Les cribles mesurent les
tokens face aux tokens ; ces trois fonds-là, personne ne les regarde.

MESURE DU JOUR, ET IL N'Y A PAS DE DÉFAUT. La seule encre réellement posée sur ces
trois fonds est `--text`, que `.choice` déclare : 10,95 / 9,88 / 10,61 en sombre,
11,03 / 11,02 / 10,92 en clair. Tout passe largement.

CE QUE LA MESURE DIT QUAND MÊME, et qui justifie ce fichier. En thème clair,
`--text-muted` sur `--surface-2` vaut **4,94:1** — au-dessus du seuil de 4,5, mais de
peu. Mélanger le moindre accent dans ce fond le fait passer **sous** le seuil :

    --text-muted sur .choice.selected (clair)   4,16:1
    --text-muted sur .choice.correct  (clair)   4,15:1
    --text-muted sur .choice.wrong    (clair)   4,11:1

Aujourd'hui aucune encre atténuée ne vit dans une `.choice`. Le jour où quelqu'un y
ajoute une ligne d'explication — « bonne réponse », « réessaie », une aide sous
l'intitulé — le réflexe est de la mettre en atténué, et elle sera illisible dans un
seul des deux thèmes. Exactement le genre de défaut que personne ne voit en le
codant, et que ce fichier fera rougir à la seconde où il apparaîtra.

Les encres ne sont pas listées à la main : elles sont **déduites** des règles qui
partagent la même classe de base et qui ne posent pas leur propre fond.
"""
from __future__ import annotations

import re
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "static" / "style.css").read_text(encoding="utf-8")

AA_TEXTE_NORMAL = 4.5
THEMES = (":root", '[data-theme="light"]')

MELANGE = re.compile(
    r"background:\s*color-mix\(in srgb,\s*var\(--([a-z0-9-]+)\)\s*(\d+)%\s*,\s*var\(--([a-z0-9-]+)\)\s*\)"
)


def _bloc(selecteur: str) -> str:
    m = re.search(re.escape(selecteur) + r"\s*\{(.*?)\}", CSS, re.S)
    assert m, f"bloc {selecteur} introuvable"
    return m.group(1)


def _token(nom: str, bloc: str) -> str:
    m = re.search(rf"--{nom}:\s*(#[0-9a-fA-F]{{3,8}})\s*;", bloc)
    assert m, f"token --{nom} introuvable dans ce thème"
    return m.group(1)


def _rgb(hexa: str) -> tuple[int, int, int]:
    h = hexa.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _srgb(canal: float) -> float:
    canal /= 255
    return canal / 12.92 if canal <= 0.03928 else ((canal + 0.055) / 1.055) ** 2.4


def luminance(c: tuple[int, int, int]) -> float:
    return 0.2126 * _srgb(c[0]) + 0.7152 * _srgb(c[1]) + 0.0722 * _srgb(c[2])


def ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def composer(teinte: str, part: int, base: str) -> tuple[int, int, int]:
    """Ce que le navigateur calcule pour `color-mix(in srgb, teinte P%, base)`."""
    p = part / 100
    return tuple(round(p * t + (1 - p) * b) for t, b in zip(_rgb(teinte), _rgb(base)))  # type: ignore[return-value]


def _regles() -> list[tuple[str, str]]:
    """(sélecteur, corps) pour chaque règle de la feuille."""
    return [(m.group(1).strip().splitlines()[-1].strip(), m.group(2))
            for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", CSS)]


def _fonds_composes() -> list[tuple[str, str, int, str]]:
    """(sélecteur, teinte, pourcentage, base) pour chaque fond calculé."""
    trouves = []
    for selecteur, corps in _regles():
        m = MELANGE.search(corps)
        if m:
            trouves.append((selecteur, m.group(1), int(m.group(2)), m.group(3)))
    return trouves


def _encres_posees_sur(selecteur: str) -> set[str]:
    """Les encres qui atterrissent VRAIMENT sur ce fond.

    Déduites, jamais listées : toute règle qui partage la classe de base (`.choice`)
    et qui ne pose pas son PROPRE fond hérite de celui-ci. Une règle qui repeint son
    fond — la pastille de lettre, par exemple — se mesure contre le sien, ailleurs.
    """
    base = "." + selecteur.lstrip(".").split(".")[0].split(" ")[0]
    encres = set()
    for autre, corps in _regles():
        if not autre.startswith(base):
            continue

        # 🔴 PREMIERE VERSION : « j'ecarte toute regle qui pose son propre fond ». Elle
        # ecartait `.choice` elle-meme — la regle qui DEFINIT le composant pose son fond
        # ET son encre, et la variante ne repeint que le fond. Resultat : zero encre
        # trouvee, et le crible aurait ete vert sur du vide. Ce qu'il faut ecarter, c'est
        # une regle DESCENDANTE qui se repeint un fond a elle (la pastille de lettre) :
        # celle-la se mesure contre le sien, ailleurs.
        descendante = autre != base
        if descendante and re.search(r"(?<!-)\bbackground:", corps):
            continue

        m = re.search(r"(?<!-)\bcolor:\s*var\(--([a-z0-9-]+)\)", corps)
        if m:
            encres.add(m.group(1))
    return encres


def test_le_crible_trouve_bien_des_fonds_composes():
    """Témoin : sans lui, un motif cassé rendrait tout le reste vert sur du vide."""
    fonds = _fonds_composes()

    assert len(fonds) >= 3, fonds
    assert any(s.startswith(".choice") for s, *_ in fonds), fonds


def test_le_calcul_est_lui_meme_verifie():
    assert round(ratio(_rgb("#000000"), _rgb("#ffffff")), 2) == 21.0
    assert round(ratio(_rgb("#777777"), _rgb("#ffffff")), 2) == 4.48

    # La composition : 50 % de blanc sur du noir doit tomber au milieu, pas à un bout.
    assert composer("#ffffff", 50, "#000000") == (128, 128, 128)


def test_le_crible_sait_quelles_encres_atterrissent_sur_ces_fonds():
    """Second témoin : une déduction qui ne trouve aucune encre rendrait tout vert."""
    encres = _encres_posees_sur(".choice.selected")

    assert "text" in encres, encres


def test_chaque_encre_se_lit_sur_le_fond_CALCULE():
    fautes = []

    for theme in THEMES:
        bloc = _bloc(theme)
        for selecteur, teinte, part, base in _fonds_composes():
            fond = composer(_token(teinte, bloc), part, _token(base, bloc))
            for encre in sorted(_encres_posees_sur(selecteur)):
                r = ratio(_rgb(_token(encre, bloc)), fond)
                if r < AA_TEXTE_NORMAL:
                    fautes.append(
                        f"{theme} {selecteur} : --{encre} sur {fond} = {r:.2f}:1"
                    )

    assert fautes == [], (
        "ces fonds n'existent nulle part dans la feuille : ils sont calculés par le "
        f"navigateur, et aucun autre crible ne les regarde — {fautes}"
    )
