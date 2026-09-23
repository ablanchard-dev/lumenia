"""Chaque écran de la page d'accueil porte exactement un titre de niveau 1.

23/09/2026 — l'audit comptait « 3 <h1> » sur la page. Ce n'était pas le défaut : les écrans
sont exclusifs (un seul visible à la fois), chacun a droit au sien. Le défaut était l'inverse :
l'écran vu en PREMIER (l'intro) et le chat n'en avaient aucun. Un lecteur d'écran qui saute de
titre en titre arrivait sur une page sans titre.
"""
from html.parser import HTMLParser

from fastapi.testclient import TestClient

from app.main import app


class _Ecrans(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pile = []      # (balise, ecran ouvert par cette balise ou None)
        self.titres = {}    # ecran -> nombre de <h1>

    def handle_starttag(self, tag, attrs):
        ident = dict(attrs).get("id") or ""
        ecran = ident if ident.startswith("screen-") else None
        if ecran:
            self.titres[ecran] = 0
        if tag == "h1":
            for _, e in reversed(self.pile):
                if e:
                    self.titres[e] += 1
                    break
        if tag not in ("meta", "link", "img", "br", "input", "path", "circle", "ellipse", "rect", "stop"):
            self.pile.append((tag, ecran))

    def handle_startendtag(self, tag, attrs):
        # `<stop .../>` : ni ouvert ni fermé. Sans ceci, la fermeture implicite vidait la pile.
        pass

    def handle_endtag(self, tag):
        if not any(t == tag for t, _ in self.pile):
            return
        while self.pile:
            t, _ = self.pile.pop()
            if t == tag:
                break


def test_chaque_ecran_porte_exactement_un_titre_de_niveau_1():
    lecteur = _Ecrans()
    lecteur.feed(TestClient(app).get("/").text)

    assert len(lecteur.titres) >= 5, f"témoin : les écrans doivent être vus ({sorted(lecteur.titres)})"
    fautifs = {e: n for e, n in lecteur.titres.items() if n != 1}
    assert fautifs == {}, f"écrans sans titre unique : {fautifs}"
