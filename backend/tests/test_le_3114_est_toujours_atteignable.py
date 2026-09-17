# -*- coding: utf-8 -*-
"""Le 3114 doit être appelable partout où il est écrit.

Mesuré le 17/09/2026 en jouant un parcours d'entrée entier dans le navigateur,
jusqu'à l'écran d'échec — un écran que personne n'avait jamais ouvert.

Sur cet écran, tous les contrastes sont bons (≥ 6,68:1), le CTA principal fait
211 × 48, et le lien **3114 fait 28 × 15 pixels**. C'est la plus petite cible de
la page, sur l'écran où la détresse est la plus probable : quelqu'un qui vient
d'échouer un parcours, sur un téléphone, peut-être les mains qui tremblent.

Pire : sur les pages 404, CGU et Confidentialité, le 3114 n'est **pas un lien du
tout** — on ne peut pas l'appeler depuis un téléphone.

Ce que ces tests figent : partout où le numéro est écrit, il est composable, et
il a la taille d'une vraie cible tactile.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
STATIC = Path(__file__).resolve().parent.parent / "static"
CSS = (STATIC / "style.css").read_text(encoding="utf-8")

PAGES_SERVIES = ["/", "/404-inexistant", "/cgu", "/confidentialite"]
NAVIGATEUR = {"accept": "text/html,application/xhtml+xml"}


def _html(chemin):
    return client.get(chemin, headers=NAVIGATEUR).text


def test_chaque_mention_du_3114_est_composable():
    """Un numéro d'urgence écrit mais pas cliquable, c'est un numéro à recopier
    à la main au moment où l'on en est le moins capable."""
    # Méthode : on retire les liens d'urgence complets, puis toutes les balises
    # (donc leurs attributs, où « tel:3114 » apparaît aussi). Ce qui reste est le
    # texte que la personne LIT. Si « 3114 » y subsiste, il est écrit sans être
    # composable. Compter naïvement les occurrences comptait l'attribut `href`
    # lui-même — le premier jet de ce test accusait des pages saines.
    lien_urgence = re.compile(r'<a[^>]*href="tel:3114"[^>]*>.*?</a>', re.S)
    balises = re.compile(r"<[^>]+>")

    manquants = {}
    for chemin in PAGES_SERVIES:
        texte_nu = balises.sub(" ", lien_urgence.sub(" ", _html(chemin)))
        restants = texte_nu.count("3114")
        if restants:
            manquants[chemin] = f"{restants} mention(s) non composable(s)"
    assert manquants == {}, manquants


def test_le_numero_a_la_taille_d_une_vraie_cible():
    """44 px de haut : la même exigence que pour la corbeille d'une conversation,
    et ici c'est le geste qui compte le plus."""
    regle = re.search(r"\.tel-urgence\s*\{([^}]*)\}", CSS)
    assert regle, "aucune règle .tel-urgence"
    contenu = regle.group(1)
    hauteur = re.search(r"min-height:\s*(\d+)px", contenu)
    assert hauteur and int(hauteur.group(1)) >= 44, contenu
    assert "inline-flex" in contenu, "une cible tactile ne peut pas rester du texte en ligne"


def test_le_numero_reste_lisible_sans_couleur():
    """Un lien qui n'est signalé que par sa couleur disparaît pour qui ne la voit
    pas : il porte aussi une bordure."""
    regle = re.search(r"\.tel-urgence\s*\{([^}]*)\}", CSS).group(1)
    assert "border" in regle


def test_la_page_404_et_les_pages_legales_le_portent_encore():
    """La garantie positive : borner ne doit pas faire disparaître le numéro."""
    for chemin in PAGES_SERVIES:
        assert "3114" in _html(chemin), chemin
