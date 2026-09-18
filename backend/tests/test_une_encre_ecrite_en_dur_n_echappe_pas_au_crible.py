# -*- coding: utf-8 -*-
"""Le crible des encres promet « toutes », et ne voyait que celles qui ont un nom.

19/09/2026. `test_aucune_encre_ne_passe_sous_le_seuil.py` s'ouvre sur cette phrase :
« Toutes les encres de la feuille de style, pas seulement celles qu'on a listées. »
Elle dit vrai pour les encres **tokenisées** : son motif est

    color:\\s*var\\(--([a-z0-9-]+)\\)

Une couleur de texte ecrite en dur — `color: #06251b` — ne correspond a rien dans ce
motif. Elle n'est donc ni mesuree, ni signalee comme oubliee : elle est **invisible** au
crible qui affirme les voir toutes. Le trou est dans la phrase qui promet.

MESURE DU JOUR, en balayant la feuille entiere : trois encres en dur, et l'une d'elles
ne se lit pas.

    .intro-wordmark              #f3eefc                     sur le fond fixe de l'intro
    .intro-tagline               rgba(236, 232, 246, .6)     sur le fond fixe de l'intro
    .choice.correct .choice-key  #06251b sur --accent        2,97:1 EN THEME CLAIR

Les deux premieres sont legitimes : `.intro` pose un fond sombre **independant du
theme**, le CSS le dit en commentaire, et une encre fixe sur un fond fixe est un choix,
pas un oubli. Elles doivent quand meme etre MESUREES — un fond fixe ne dispense pas de
se lire.

La troisieme est un defaut. C'est la pastille de lettre de la **bonne reponse** dans une
epreuve : ce que quelqu'un regarde juste apres avoir repondu. En theme clair, `--accent`
vaut `#047857`, un vert fonce, et l'encre `#06251b` est quasi noire : 2,97:1 la ou WCAG
AA demande 4,5:1. En theme sombre le meme couple donne 10,69:1 — le defaut ne se voit
que dans un theme, ce qui est exactement pourquoi une couleur en dur est dangereuse.

Et la regle SŒUR, deux lignes plus haut, fait la meme chose correctement :

    .choice.selected .choice-key { ... color: var(--on-primary); }
    .choice.correct  .choice-key { ... color: #06251b; }

Deux regles voisines, le meme role, une seule passe par un token. Le motif le plus
frequent de cette boucle.

CE QUE CE FICHIER VERROUILLE : toute encre ecrite en dur doit etre DECLAREE ici avec le
fond sur lequel elle est posee, et s'y lire. Une nouvelle couleur en dur fait rougir le
crible au lieu de passer sous le radar.
"""
from __future__ import annotations

import re
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "static" / "style.css").read_text(encoding="utf-8")

AA_TEXTE_NORMAL = 4.5

# Le fond de `.intro` est un degrade radial fixe, independant du theme :
#   radial-gradient(circle at 50% 42%, #121829 0%, #0a0e1a 52%, #06080f 100%)
# Le pire cas pour une encre claire est l'arret le plus CLAIR du degrade.
FOND_INTRO = "#121829"

# Encre en dur -> le fond sur lequel elle est reellement posee.
# Une entree ici est une decision assumee, pas une dispense : le ratio est mesure.
ENCRES_EN_DUR = {
    ".intro-wordmark": ("#f3eefc", FOND_INTRO),
    ".intro-tagline": ("rgba(236, 232, 246, .6)", FOND_INTRO),
}


def _srgb(canal: float) -> float:
    canal /= 255
    return canal / 12.92 if canal <= 0.03928 else ((canal + 0.055) / 1.055) ** 2.4


def _composantes(couleur: str) -> tuple[float, float, float, float]:
    """(r, g, b, alpha) d'un `#rgb`, `#rrggbb` ou `rgba(r, g, b, a)`."""
    couleur = couleur.strip()
    if couleur.startswith("rgb"):
        nombres = re.findall(r"[\d.]+", couleur)
        r, g, b = (float(n) for n in nombres[:3])
        a = float(nombres[3]) if len(nombres) > 3 else 1.0
        return r, g, b, a
    h = couleur.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0


def luminance(couleur: str, fond: str = "#000000") -> float:
    """Luminance d'une couleur, APRES composition sur son fond si elle est translucide.

    Sans cette composition, `rgba(236, 232, 246, .6)` serait mesuree comme si elle etait
    opaque — c'est-a-dire plus lisible qu'elle ne l'est reellement.
    """
    r, g, b, a = _composantes(couleur)
    if a < 1.0:
        fr, fg, fb, _ = _composantes(fond)
        r, g, b = (a * c + (1 - a) * f for c, f in ((r, fr), (g, fg), (b, fb)))
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)


def ratio(encre: str, fond: str) -> float:
    la, lb = luminance(encre, fond), luminance(fond)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _encres_en_dur_du_css() -> dict[str, str]:
    """Selecteur -> couleur, pour toute declaration `color:` qui n'est pas un token."""
    trouvees: dict[str, str] = {}
    for regle in re.finditer(r"([^{}]+)\{([^{}]*)\}", CSS):
        selecteur = regle.group(1).strip().splitlines()[-1].strip()
        for declaration in re.finditer(r"(?<!-)\bcolor:\s*([^;]+);", regle.group(2)):
            valeur = declaration.group(1).strip()
            if valeur.startswith(("#", "rgb")) or valeur in ("white", "black"):
                trouvees[selecteur] = valeur
    return trouvees


def test_le_calcul_est_lui_meme_verifie():
    """Deux reperes connus, sinon ce fichier n'est qu'une opinion chiffree."""
    assert round(ratio("#000000", "#ffffff"), 2) == 21.0
    assert round(ratio("#777777", "#ffffff"), 2) == 4.48

    # Et la composition : du blanc a 50 % sur du noir doit valoir un gris moyen, pas du
    # blanc. Sans ce repere, l'alpha pourrait etre ignore sans que rien ne bouge.
    assert ratio("rgba(255, 255, 255, .5)", "#000000") < ratio("#ffffff", "#000000")


def test_le_crible_voit_bien_la_feuille():
    """Temoin : un motif casse rendrait tout le reste vert sur du vide."""
    assert len(CSS) > 10_000
    assert re.search(r"(?<!-)\bcolor:\s*var\(--", CSS), "aucune encre tokenisee trouvee"


def test_aucune_encre_en_dur_n_est_inconnue_du_crible():
    """Le verrou : une nouvelle couleur en dur doit etre declaree, pas subie."""
    inconnues = sorted(set(_encres_en_dur_du_css()) - set(ENCRES_EN_DUR))

    assert inconnues == [], (
        "ces selecteurs codent une couleur de texte en dur sans etre declares ici. Une "
        "couleur en dur echappe aux deux themes : passez par un token, ou declarez-la "
        f"avec le fond sur lequel elle est posee — {inconnues}"
    )


def test_chaque_encre_en_dur_se_lit_sur_son_fond():
    fautes = [
        f"{selecteur} : {encre} sur {fond} = {ratio(encre, fond):.2f}:1"
        for selecteur, (encre, fond) in ENCRES_EN_DUR.items()
        if ratio(encre, fond) < AA_TEXTE_NORMAL
    ]

    assert fautes == [], f"WCAG AA demande {AA_TEXTE_NORMAL}:1 — {fautes}"


def test_la_pastille_de_la_BONNE_REPONSE_passe_par_un_token():
    """Le defaut du jour, verrouille nommement.

    Sa regle sœur `.choice.selected .choice-key` passe par `var(--on-primary)` depuis
    toujours. Celle-ci codait `#06251b`, invisible au crible des encres, et 2,97:1 en
    theme clair — sur la pastille que quelqu'un regarde juste apres avoir repondu.
    """
    regle = re.search(r"\.choice\.correct \.choice-key\s*\{([^}]*)\}", CSS)
    assert regle, "la regle de la pastille de bonne reponse a disparu"

    couleur = re.search(r"(?<!-)\bcolor:\s*([^;]+);", regle.group(1))
    assert couleur, "cette pastille ne declare plus de couleur de texte"
    assert "var(--" in couleur.group(1), (
        f"la pastille code '{couleur.group(1).strip()}' : une couleur en dur ne suit pas "
        "le theme, et en clair celle-ci donnait 2,97:1"
    )
