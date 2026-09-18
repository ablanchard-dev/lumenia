# -*- coding: utf-8 -*-
"""Deux noms pour le même fichier, et c'est le serveur qui gagne.

18/09/2026. L'écran propose l'export du journal par ce lien :

    <a id="export-journal" href="/journal/export" download="lumenia-journal.csv">

et le serveur répond :

    content-disposition: attachment; filename=journal.csv

Ce n'est pas un partage d'avis : la spécification HTML est claire, l'attribut
`download` est **ignoré** quand la réponse porte un `Content-Disposition` avec un
nom de fichier. Le serveur gagne toujours, donc l'utilisateur reçoit
`journal.csv` — un nom générique dans un dossier de téléchargements, sur un
fichier qu'on lui dit de transmettre à son psy. Celui qui l'ouvre trois semaines
plus tard ne sait pas d'où il vient.

Le correctif ne choisit pas un camp : il tient les deux ensemble. Le test lit le
nom **dans la page** et le compare à celui que le serveur envoie, donc changer
l'un sans l'autre rougit.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
INDEX = Path(__file__).resolve().parent.parent / "static" / "index.html"


def _nom_promis_par_l_ecran() -> str | None:
    trouve = re.search(r'id="export-journal"[^>]*download="([^"]+)"', INDEX.read_text(encoding="utf-8"))
    return trouve.group(1) if trouve else None


def _nom_envoye_par_le_serveur() -> str | None:
    entete = client.get("/journal/export").headers.get("content-disposition", "")
    trouve = re.search(r'filename="?([^";]+)"?', entete)
    return trouve.group(1).strip() if trouve else None


def test_le_crible_lit_bien_les_deux_noms():
    """Témoin : sans lui, un lien renommé rendrait le test suivant vert sur du vide."""
    assert _nom_promis_par_l_ecran() is not None, "l'écran doit toujours proposer l'export"
    assert _nom_envoye_par_le_serveur() is not None, "la réponse doit toujours nommer le fichier"


def test_l_ecran_et_le_serveur_nomment_le_meme_fichier():
    promis = _nom_promis_par_l_ecran()
    envoye = _nom_envoye_par_le_serveur()

    assert promis == envoye, (
        f"l'écran promet « {promis} », le serveur envoie « {envoye} ». L'attribut `download` est "
        "ignoré dès que la réponse porte un Content-Disposition nommé : c'est le serveur qui gagne, "
        "et l'utilisateur reçoit un nom qu'on ne lui a jamais montré"
    )


def test_le_nom_dit_de_quel_produit_il_vient():
    """L'autre sens : les tenir égaux ne suffirait pas s'ils valaient tous deux `export.csv`."""
    envoye = _nom_envoye_par_le_serveur()

    assert "lumenia" in envoye.lower(), (
        f"« {envoye} » ne dit pas d'où il vient. Ce fichier est fait pour être transmis, puis "
        "rouvert des semaines plus tard, dans un dossier qui en contient cent autres"
    )
    assert envoye.endswith(".csv")
