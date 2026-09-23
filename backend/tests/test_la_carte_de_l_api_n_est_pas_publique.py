"""23/09/2026 — La carte complete de l'API n'est pas servie a n'importe qui.

Audit avant production (N-1) : `/docs`, `/redoc` et `/openapi.json` repondaient 200 a tout
visiteur. robots.txt les interdisait aux moteurs, mais un humain les lit quand meme : c'est la
liste de chaque route, de chaque champ et de ses bornes -- le plan d'attaque, offert.

Ils restent disponibles pour qui developpe : `LUMENIA_DOCS=1`.
"""
import importlib

import pytest
from fastapi.testclient import TestClient


def _app(monkeypatch, valeur):
    if valeur is None:
        monkeypatch.delenv("LUMENIA_DOCS", raising=False)
    else:
        monkeypatch.setenv("LUMENIA_DOCS", valeur)
    import app.main as principal
    return importlib.reload(principal).app


@pytest.mark.parametrize("route", ["/docs", "/redoc", "/openapi.json"])
def test_par_defaut_la_carte_de_l_api_n_est_pas_servie(monkeypatch, route):
    assert TestClient(_app(monkeypatch, None)).get(route).status_code == 404


def test_un_developpeur_peut_la_rouvrir(monkeypatch):
    # Temoin : sans lui, une app qui ne sert plus RIEN passerait le test du dessus.
    assert TestClient(_app(monkeypatch, "1")).get("/openapi.json").status_code == 200


def test_une_entree_de_journal_vide_est_refusee():
    # N-3 : titre et contenu vides donnaient 200 et une ligne vide en base.
    from app.main import app
    r = TestClient(app).post("/journal", json={"title": "", "content": ""})
    assert r.status_code == 422


def test_un_titre_vide_avec_du_contenu_reste_accepte():
    # On borne le vide, pas le style : ecrire sans titre est un usage normal d'un journal.
    from app.main import app
    r = TestClient(app).post("/journal", json={"title": "", "content": "ce matin, rien de special"})
    assert r.status_code == 200
