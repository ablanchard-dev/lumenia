"""Gate serveur : l'accompagnement (/chat) n'est ouvert qu'apres validation du parcours
d'entree (seuil ENTRY_PASS_RATIO), enforce cote SERVEUR et pas seulement au front. La
ressource de crise (3114) reste toujours visible, meme quand le chat est bloque."""
from fastapi.testclient import TestClient

from app.entry import entry_passed, ENTRY_PASS_RATIO
from app.main import app


def test_entry_passed_threshold():
    assert ENTRY_PASS_RATIO == 0.85
    assert entry_passed(26, 30) is True          # 0.867 >= 0.85
    assert entry_passed(25, 30) is False         # 0.833 < 0.85
    assert entry_passed(30, 30) is True
    assert entry_passed(0, 30) is False
    assert entry_passed(0, 0) is False           # pas de division par zero


def _results(nok, total=30):
    return [{"id": str(i), "dimension": "logique", "ok": i < nok, "skipped": False, "answer": ""}
            for i in range(total)]


def test_chat_is_gated_server_side_until_entry_passed():
    c = TestClient(app)
    # Echec du parcours -> /chat bloque, mais le 3114 reste visible (securite).
    c.post("/entry/complete", json={"results": _results(10)})
    g = c.post("/chat", json={"message": "aide moi", "history": []}).json()
    assert g.get("gated") is True
    assert "3114" in g.get("reply", "")

    # Reussite (28/30 = 93%) -> le gate s'ouvre, vraie reponse d'accompagnement.
    comp = c.post("/entry/complete", json={"results": _results(28)}).json()
    assert comp["passed"] is True
    ok = c.post("/chat", json={"message": "aide moi a organiser ma journee", "history": []}).json()
    assert not ok.get("gated")
    assert ok.get("reply")

    # Nouvel echec -> re-bloque (l'etat serveur suit le dernier parcours).
    c.post("/entry/complete", json={"results": _results(20)})
    g2 = c.post("/chat", json={"message": "aide", "history": []}).json()
    assert g2.get("gated") is True


def test_crisis_bypasses_gate():
    # SECURITE : une detresse aigue prime sur le gate. En etat NON valide, un message de
    # crise doit recevoir la reponse de crise (3114 + risk_flag), pas le message « finis
    # ton test a 85% ». La crise court-circuite le controle d'acces.
    c = TestClient(app)
    c.post("/entry/complete", json={"results": _results(5)})   # parcours echoue -> gated
    r = c.post("/chat", json={"message": "je veux mourir", "history": []}).json()
    assert r.get("gated") is not True
    assert r.get("risk_flag") is True
    assert "3114" in r.get("reply", "")


# --- Le dénominateur ne doit pas venir du client -----------------------------
# Le seuil est un RATIO. Tant que `total` valait `len(results)`, un appel direct
# envoyant UN SEUL item juste obtenait 1/1 = 100 % et ouvrait le chat : le gate
# était bien côté serveur, mais il faisait confiance au client sur le nombre
# d'épreuves. Trouvé en l'exécutant le 15/08, pas en relisant le code.

def test_entry_is_complete_derive_sa_longueur_du_tirage():
    from app.entry import entry_is_complete, entry_scored_length, get_parcours
    attendu = entry_scored_length()
    assert attendu == get_parcours()["total"], \
        "le garde-fou et le tirage doivent parler de la même longueur"
    assert entry_is_complete(attendu) is True
    assert entry_is_complete(attendu - 1) is False
    assert entry_is_complete(attendu + 1) is False
    assert entry_is_complete(0) is False


def test_un_parcours_tronque_ne_passe_pas_meme_avec_100_pourcent():
    c = TestClient(app)
    r = c.post("/entry/complete", json={"results": _results(1, total=1)}).json()
    assert r["score"] == 1 and r["total"] == 1
    assert r["passed"] is False, "1/1 = 100 % ne doit PAS valider un parcours de 30"
    g = c.post("/chat", json={"message": "aide moi", "history": []}).json()
    assert g.get("gated") is True


def test_un_parcours_rembourre_ne_passe_pas_non_plus():
    # L'autre côté de la borne : ajouter des items ne doit pas non plus ouvrir le gate.
    c = TestClient(app)
    r = c.post("/entry/complete", json={"results": _results(31, total=31)}).json()
    assert r["passed"] is False


def test_le_parcours_legitime_passe_toujours():
    # Garde-fou du garde-fou : la longueur exacte doit rester acceptée.
    c = TestClient(app)
    assert c.post("/entry/complete", json={"results": _results(26)}).json()["passed"] is True
    assert c.post("/entry/complete", json={"results": _results(25)}).json()["passed"] is False


# --- Une panne de correcteur n'est pas un verdict sur la personne ------------
# `/entry/verify` distingue deja "faux" de "juge injoignable" (`undetermined`),
# mais le drapeau s'arretait au front : le serveur ne voyait qu'un `ok=False` de
# plus. Avec ~14,65 epreuves a reponse libre sur 30 et 4 erreurs permises, une
# panne de juge rendait le parcours quasi impassable — en annoncant a la personne
# qu'elle avait echoue un test cognitif.

def _res(nok, total=30, undet_idx=()):
    return [{"id": str(i), "dimension": "logique", "ok": i < nok, "skipped": False,
             "answer": "", "undetermined": i in undet_idx} for i in range(total)]


def test_un_item_non_juge_empeche_le_verdict_meme_si_le_score_suffit():
    c = TestClient(app)
    # 29 bonnes reponses sur 30 : largement au-dessus du seuil. Mais une epreuve
    # n'a pas pu etre corrigee -> on ne prononce pas.
    r = c.post("/entry/complete", json={"results": _res(29, undet_idx=(29,))}).json()
    assert r["passed"] is False
    assert r["undetermined"] is True, "le serveur doit dire qu'il n'a pas pu corriger"


def test_un_parcours_entierement_juge_reste_normal():
    c = TestClient(app)
    r = c.post("/entry/complete", json={"results": _res(26)}).json()
    assert r["passed"] is True
    assert r["undetermined"] is False


def test_un_echec_franc_n_est_pas_deguise_en_panne():
    # Le symetrique : une vraie erreur doit rester une vraie erreur.
    c = TestClient(app)
    r = c.post("/entry/complete", json={"results": _res(20)}).json()
    assert r["passed"] is False
    assert r["undetermined"] is False, "un echec reel ne doit pas passer pour une panne"


def test_les_items_non_juges_ne_sortent_PAS_du_denominateur():
    # Les exclure abaisserait le seuil en silence : ce serait rouvrir la faille du
    # denominateur pilote par le client (corrigee a l'iteration 103).
    c = TestClient(app)
    r = c.post("/entry/complete", json={"results": _res(30, undet_idx=(0, 1, 2))}).json()
    assert r["total"] == 30, "le denominateur doit rester la longueur du parcours"


def test_le_client_par_defaut_reste_compatible():
    # Les clients qui n'envoient pas le champ ne doivent pas changer de comportement.
    c = TestClient(app)
    sans_champ = [{"id": str(i), "dimension": "logique", "ok": i < 26, "skipped": False, "answer": ""}
                  for i in range(30)]
    r = c.post("/entry/complete", json={"results": sans_champ}).json()
    assert r["passed"] is True and r["undetermined"] is False
