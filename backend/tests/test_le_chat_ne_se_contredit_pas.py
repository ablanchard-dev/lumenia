"""Le chat ne montre pas deux fois le même libellé pour deux choses, et son 3114 se voit.

23/09/2026 — critique Impeccable du chat (deux évaluations) :
- le bouton « Nouvelle conversation » et, juste dessous, une conversation vide portant EXACTEMENT
  le même nom : deux éléments cliquables, un seul libellé, deux actions. Pour ce public, c'est
  l'ambiguïté qui coûte (quelle est la règle ?) ;
- sous la zone de saisie, le 3114 se fondait dans le gris de l'avertissement générique.
"""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_une_conversation_vide_ne_porte_pas_le_nom_du_bouton():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    bouton = re.search(r'<button id="new-chat"[^>]*>\s*(?:<svg.*?</svg>)?\s*([^<]+?)\s*</button>', html, re.S)
    assert bouton, "témoin : le bouton de nouvelle conversation doit être lu"
    titre = (re.search(r'const TITRE_VIDE = "([^"]+)"', js)
             or re.search(r'title:\s*"([^"]+)"', js[js.index("function createConv"):]))
    assert titre, "témoin : le titre par défaut doit être lu"
    assert titre.group(1) != bouton.group(1).strip()


def test_le_3114_du_bas_se_detache_de_l_avertissement():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    note = re.search(r'<p class="composer-note">(.*?)</p>', html, re.S)
    assert note, "témoin : la note sous la zone de saisie doit exister"
    lien = re.search(r'<a [^>]*href="tel:3114"[^>]*>', note.group(1))
    assert lien and "class=" in lien.group(0), "le 3114 du bas n'a aucun style propre"
