"""23/09/2026 — UN VISITEUR NE LIT JAMAIS CE QU'UN AUTRE A ECRIT.

Audit avant production, exploit execute sur le serveur local, sans compte ni en-tete :
`GET /journal` rendait le journal de TOUT le monde (« je veux mourir » compris),
`GET /journal/export` en faisait un CSV, et `GET /risk` rendait un drapeau de risque
suicidaire GLOBAL : celui d'une personne s'affichait a la suivante. Le parcours d'entree
aussi etait global : une personne qui le reussissait l'ouvrait pour tout le monde.

Lumenia reste sans compte : chaque navigateur tire un identifiant aleatoire opaque
(`crypto.randomUUID()`) et le presente dans `X-Lumenia-Id`. Il n'est pas un cookie —
il ne part que dans les requetes que la page fait elle-meme. Sans lui, pas d'etat.
"""
import uuid

from fastapi.testclient import TestClient

from app.main import app


def _client(visiteur):
    return TestClient(app, headers={"X-Lumenia-Id": visiteur})


def test_le_journal_de_A_n_apparait_ni_dans_la_liste_ni_dans_l_export_de_B():
    a, b = _client(str(uuid.uuid4())), _client(str(uuid.uuid4()))
    secret = "contenu prive de A " + uuid.uuid4().hex
    assert a.post("/journal", json={"title": "soir", "content": secret}).status_code == 200

    assert secret in str(a.get("/journal").json()), "temoin : A relit bien sa propre entree"
    assert secret in a.get("/journal/export").text

    assert secret not in str(b.get("/journal").json())
    assert secret not in b.get("/journal/export").text


def test_le_drapeau_de_risque_de_A_ne_s_affiche_pas_chez_B():
    a, b = _client(str(uuid.uuid4())), _client(str(uuid.uuid4()))
    assert a.post("/chat", json={"message": "je veux mourir", "history": []}).json()["risk_flag"] is True
    assert a.get("/risk").json()["risk_flag"] is True, "temoin"
    assert b.get("/risk").json()["risk_flag"] is False


def test_le_profil_de_A_n_est_pas_celui_de_B():
    a, b = _client(str(uuid.uuid4())), _client(str(uuid.uuid4()))
    a.post("/profile", json={"low_stim": False, "font_size": 22, "pacing": "slow"})
    assert a.get("/profile").json()["font_size"] == 22, "temoin"
    assert b.get("/profile").json()["font_size"] != 22


def test_sans_identifiant_aucun_etat_n_est_lu_et_le_refus_porte_le_3114():
    anonyme = TestClient(app, headers={"X-Lumenia-Id": ""})
    for methode, route in (("get", "/journal"), ("get", "/journal/export"), ("get", "/risk"),
                           ("get", "/profile"), ("get", "/consent")):
        r = getattr(anonyme, methode)(route)
        assert r.status_code == 401, route
        assert "3114" in r.text, route


def test_un_identifiant_devinable_est_refuse():
    # « 1 » ou « admin » se devinent : l'identifiant EST la frontiere, il doit etre aleatoire.
    for devinable in ("1", "admin", "00000000-0000-0000-0000-000000000000","x" * 200):
        r = TestClient(app, headers={"X-Lumenia-Id": devinable}).get("/journal")
        assert r.status_code == 401, devinable
