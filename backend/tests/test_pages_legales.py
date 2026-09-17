# -*- coding: utf-8 -*-
"""Les pages legales ne sont pas de la prose : ce sont des affirmations verifiables.

Le piege habituel d'une politique de confidentialite, c'est qu'elle est copiee
d'ailleurs et qu'elle decrit un autre produit. Ici, les tests la confrontent au
CODE : si une page annonce moins de fournisseurs que `llm.py` peut appeler, ou
oublie une table que le serveur ecrit vraiment, elle rougit.
"""
import re

from fastapi.testclient import TestClient

from app import llm, models
from app.main import app

client = TestClient(app)
NAVIGATEUR = {"accept": "text/html,application/xhtml+xml"}


def page(chemin):
    r = client.get(chemin, headers=NAVIGATEUR)
    assert r.status_code == 200, chemin
    assert r.headers["content-type"].startswith("text/html")
    return r.text


def test_les_deux_pages_existent():
    assert "Confidentialité" in page("/confidentialite")
    assert "Conditions" in page("/cgu")


def test_elles_sont_atteignables_depuis_l_accueil():
    """Une page legale qu'aucun lien ne designe n'existe pas pour l'utilisateur."""
    accueil = page("/")
    assert 'href="/confidentialite"' in accueil
    assert 'href="/cgu"' in accueil


def test_la_page_confidentialite_nomme_TOUS_les_fournisseurs_que_le_code_peut_appeler():
    texte = page("/confidentialite").lower()
    for fournisseur in llm._PROVIDERS:
        assert fournisseur in texte, f"{fournisseur} peut recevoir des messages et n'est pas annonce"


def test_elle_nomme_TOUTES_les_tables_que_le_serveur_ecrit():
    texte = page("/confidentialite")
    tables = {c.__tablename__ for c in (models.KV, models.Profile, models.Journal, models.Assessment)}
    for table in tables:
        assert table in texte, f"la table {table} est ecrite et n'est pas annoncee"


def test_elle_dit_que_des_donnees_de_sante_sont_en_jeu():
    """PHQ-9 et GAD-7 sont des questionnaires cliniques : article 9 du RGPD."""
    texte = page("/confidentialite")
    assert "PHQ-9" in texte and "GAD-7" in texte
    assert "article 9" in texte.lower()


def test_elle_ne_promet_pas_de_cookie_alors_qu_il_n_y_en_a_aucun():
    texte = page("/confidentialite").lower()
    assert "aucun cookie" in texte
    # Et la promesse reste verifiee par le vrai comportement :
    r = client.get("/confidentialite")
    assert "set-cookie" not in {k.lower() for k in r.headers}


def test_elle_annonce_le_transfert_hors_UE():
    """Google, Cerebras et Groq sont hors UE : le dire est une obligation, pas un detail."""
    texte = page("/confidentialite").lower()
    assert "hors de l'union européenne" in texte or "hors ue" in texte


def test_les_droits_rgpd_sont_enumeres():
    texte = page("/confidentialite").lower()
    for droit in ("accès", "rectification", "effacement", "opposition", "portabilité"):
        assert droit in texte, droit
    assert "cnil" in texte


def test_les_cgu_disent_ce_que_lumenia_n_est_pas():
    texte = page("/cgu")
    assert "n'est pas un dispositif médical" in texte
    assert "3114" in texte
    assert "16 ans" in texte  # age minimum, cohérent avec le RGPD français


def test_les_pages_legales_sont_dans_le_sitemap():
    xml = client.get("/sitemap.xml").text
    assert "/confidentialite" in xml and "/cgu" in xml


def test_ce_qui_attend_alex_est_visible_et_compte():
    """Le nom et le contact du responsable ne s'inventent pas. Tant qu'ils manquent,
    la page le DIT au lecteur au lieu de faire semblant -- et ce test compte les trous
    pour qu'ils ne se perdent pas."""
    texte = page("/confidentialite")
    trous = re.findall(r'data-a-completer="([^"]+)"', texte)
    assert set(trous) == {"identite-responsable", "contact-responsable", "hebergeur"}, trous
    assert "à compléter" in texte.lower()
