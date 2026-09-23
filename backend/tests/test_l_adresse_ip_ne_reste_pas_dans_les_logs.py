"""La page de confidentialité promet que l'adresse IP n'est pas conservée.

23/09/2026 — vrai pour l'anti-spam (condensat salé), faux pour le journal d'accès d'uvicorn :
chaque requête y écrivait `IP:port - "POST /chat"`, et `docker logs` le garde tant que le
conteneur existe. Tout lancement exposé (`--host 0.0.0.0`) livré dans le dépôt doit donc
couper ce journal.
"""
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
LANCEURS = [RACINE / "backend" / "Dockerfile", RACINE / "docker-compose.yml"]


def _lancements_exposes():
    trouves = []
    for f in LANCEURS:
        for n, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if "uvicorn" in ligne and re.search(r"0\.0\.0\.0", ligne):
                trouves.append((f"{f.name}:{n}", ligne))
    return trouves


def test_la_promesse_de_la_page_existe_toujours():
    page = (RACINE / "backend" / "static" / "confidentialite.html").read_text(encoding="utf-8")
    assert "adresse IP</strong> n'y est pas conservée" in page


def test_aucun_lancement_expose_ne_garde_l_ip_dans_son_journal():
    lancements = _lancements_exposes()
    assert len(lancements) >= 2, "témoin : le Dockerfile et le compose doivent être lus"
    fautifs = [ou for ou, ligne in lancements if "--no-access-log" not in ligne]
    assert fautifs == [], f"journal d'accès uvicorn actif (IP en clair) : {fautifs}"


def test_aucun_lancement_expose_n_annonce_son_serveur():
    # 23/09/2026 (repasse de la grille) : chaque réponse portait « server: uvicorn ». Rien ne sert
    # à le dire, et c'est la première ligne d'un inventaire pour qui cherche une faille connue.
    fautifs = [ou for ou, ligne in _lancements_exposes() if "--no-server-header" not in ligne]
    assert fautifs == [], f"en-tête server annoncé : {fautifs}"
