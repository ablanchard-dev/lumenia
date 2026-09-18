# -*- coding: utf-8 -*-
"""L'anti-spam a besoin de distinguer les visiteurs, pas de savoir qui ils sont.

18/09/2026. Mesure du jour : `limite._vues` était indexé par l'adresse IP **en
clair** (`request.client.host`). Une adresse IP est une donnée personnelle — la
CJUE l'a tranché dans *Breyer* (C-582/14) — et Lumenia est une application de
santé mentale : la mémoire du serveur reliait une IP aux moments exacts où
quelqu'un a écrit à un compagnon de crise.

Pire, la politique de confidentialité affirmait que le serveur enregistre
« exactement quatre tables ». C'était faux, et c'est la page qui doit être
exhaustive. Le trou était dans la phrase qui promet.

Le limiteur n'a jamais eu besoin de l'adresse : il lui faut une clé stable le
temps d'une fenêtre d'une minute. Un condensat salé au démarrage suffit, et le
sel change à chaque redémarrage — la clé n'est donc réversible ni en mémoire,
ni dans un vidage de processus, ni d'un jour sur l'autre.
"""
import re
from pathlib import Path

from app import limite

RACINE = Path(__file__).resolve().parent.parent
IP_EN_CLAIR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\b[0-9a-f]{0,4}:[0-9a-f:]{2,}\b", re.I)


def _memoire_du_limiteur() -> list[str]:
    return [str(cle) for cle in limite._vues]


def test_aucune_adresse_ip_ne_reste_lisible_en_memoire():
    limite.reinitialiser()
    for adresse in ("203.0.113.7", "198.51.100.42", "2001:db8::1"):
        limite.autorise(limite.cle_de(adresse))

    lisibles = [cle for cle in _memoire_du_limiteur() if IP_EN_CLAIR.search(cle)]
    assert lisibles == [], f"des adresses restent lisibles dans la mémoire du limiteur : {lisibles}"


def test_le_crible_reconnait_bien_une_adresse():
    """Témoin inverse : sans lui, un motif cassé rendrait le test ci-dessus muet."""
    assert IP_EN_CLAIR.search("203.0.113.7")
    assert IP_EN_CLAIR.search("2001:db8::1")
    assert not IP_EN_CLAIR.search("a3f19c2b8d4e6071")


def test_deux_visiteurs_restent_distincts():
    """La garantie positive : anonymiser ne doit pas fondre tout le monde en une
    seule clé — ce qui ferait tomber le quota du premier sur le suivant."""
    limite.reinitialiser()
    a, b = limite.cle_de("203.0.113.7"), limite.cle_de("198.51.100.42")
    assert a != b

    for _ in range(limite.PAR_MINUTE):
        assert limite.autorise(a)[0]
    assert limite.autorise(a)[0] is False, "le quota doit finir par se fermer"
    assert limite.autorise(b)[0] is True, "le voisin ne doit pas payer pour lui"


def test_la_meme_adresse_donne_la_meme_cle_dans_une_meme_vie():
    """Sinon l'anti-spam ne limite plus rien : chaque requête serait un inconnu."""
    assert limite.cle_de("203.0.113.7") == limite.cle_de("203.0.113.7")


def test_le_middleware_reel_n_ecrit_pas_l_adresse_en_memoire():
    """Le garde au bon endroit : anonymiser dans `cle_de` ne sert a rien si le
    middleware appelle `autorise(client_de(request))` directement. On passe donc
    par l'application reelle, avec une adresse connue, et on regarde la memoire."""
    from fastapi.testclient import TestClient

    from app.main import app

    limite.reinitialiser()
    client = TestClient(app, client=("203.0.113.7", 51000))
    client.post("/chat", json={"message": "bonjour", "history": []})

    memoire = _memoire_du_limiteur()
    assert memoire, "sans trace en memoire, ce test serait vert sur le vide"
    assert "203.0.113.7" not in memoire, memoire
    limite.reinitialiser()


def test_la_politique_dit_ce_que_l_anti_spam_garde():
    """La page qui affirme « exactement quatre tables » doit aussi nommer la
    mémoire vive de l'anti-spam, sinon son exhaustivité est un mensonge."""
    texte = (RACINE / "static" / "confidentialite.html").read_text(encoding="utf-8")
    sans_balises = re.sub(r"<[^>]+>", " ", texte)
    assert re.search(r"anti-spam|limitation de d[ée]bit", sans_balises, re.I), sans_balises[:400]
    assert re.search(r"adresse IP", sans_balises, re.I)
