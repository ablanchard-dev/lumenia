"""Le halo de l'accueil ne rend pas défilable un chat qui n'a encore rien à montrer.

23/09/2026, mesuré à 375 x 812 : la zone des messages, vide, défilait de 158 px. Le coupable
n'était pas un message mais le halo décoratif de l'accueil (`.welcome::before`), étendu de 60 %
sous l'accueil pour un dégradé déjà transparent à cette hauteur : du vide qui allonge le défilement.
Le halo s'arrête donc au bas de l'accueil ; seuls ses côtés et son haut débordent.
"""
import re
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "static" / "style.css").read_text(encoding="utf-8")


def _bas_du_halo():
    bloc = re.search(r"\.welcome::before\s*\{([^}]*)\}", CSS)
    assert bloc, "témoin : le halo de l'accueil existe"
    inset = re.search(r"\binset:\s*([^;]+);", bloc.group(1))
    assert inset, "témoin : le halo est placé par `inset`"
    v = inset.group(1).split()
    # inset: haut [droite [bas [gauche]]] — le bas vaut le haut quand il n'est pas écrit
    return v[2] if len(v) >= 3 else v[0]


def test_le_halo_ne_descend_pas_sous_l_accueil():
    bas = _bas_du_halo()
    assert not bas.startswith("-"), f"le halo descend sous l'accueil ({bas}) : le chat vide défile"
