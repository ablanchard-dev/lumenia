"""Qui revient après avoir passé le seuil arrive dans le chat, sans rejouer l'intro.

23/09/2026 — critique Impeccable (#4) : l'intro animée se jouait à CHAQUE ouverture, suivie d'un clic
obligatoire, même pour la personne qui revient simplement parler. Pour un outil qui se veut
peu stimulant, c'est une mise en scène imposée à chaque visite. Les recommandations de lancement
(Android) : une animation d'ouverture doit pouvoir être sautée, jamais retarder sans raison.

La première visite garde l'intro ; la personne en pause aussi (l'intro lui dit où elle en est).
"""
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_le_demarrage_envoie_directement_au_chat_qui_a_deja_passe_le_seuil():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    init = js[js.index("(async function init()"):]
    fin = init.index("})();")
    corps = init[:fin]
    passe = corps.find('getItem("lumenia.entryPassed") === "1"')
    assert passe != -1, "le démarrage ne regarde pas si le seuil est déjà passé"
    suite = corps[passe:passe + 300]
    assert "hideIntroNow" in suite and "enterChat" in suite, "qui a passé le seuil rejoue encore l'intro"
