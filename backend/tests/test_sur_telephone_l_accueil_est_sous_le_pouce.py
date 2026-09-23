"""Sur un téléphone, l'accueil du chat se pose contre la zone de saisie, sous le pouce.

23/09/2026 — critique Impeccable du chat (E) puis mesure à 375 x 812 : 69 px au-dessus de l'accueil,
206 px de vide entre les suggestions et la zone de saisie. Le groupe « titre, suggestions, saisie »
était coupé en deux. Hoober (1 300+ personnes observées) : à une main, le tiers bas de l'écran est
la seule zone sans effort. Sur écran étroit, l'accueil descend donc contre la saisie ; l'ordinateur
garde sa mise en page.
"""
import re
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "static" / "style.css").read_text(encoding="utf-8")


def test_sur_ecran_etroit_l_accueil_se_pose_contre_la_saisie():
    blocs = re.findall(r"@media\s*\(max-width:\s*(\d+)px\)\s*\{(.*?)\n\}", CSS, re.S)
    assert blocs, "témoin : la feuille doit avoir des règles pour écran étroit"
    etroits = "".join(corps for largeur, corps in blocs if int(largeur) <= 720)
    assert re.search(r"\.messages:has\(>\s*\.welcome\)\s*\{[^}]*flex-direction:\s*column", etroits), \
        "la zone des messages ne se range pas en colonne quand elle n'affiche que l'accueil"
    assert re.search(r"\.messages\s*>\s*\.welcome\s*\{[^}]*margin:\s*auto", etroits), \
        "l'accueil ne descend pas contre la zone de saisie"
