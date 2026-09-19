# -*- coding: utf-8 -*-
"""Le fichier qu'on copie pour configurer Lumenia n'en déclare que la moitié.

19/09/2026. `backend/.env.example` est le premier geste de quiconque déploie ce produit —
le README le dit (`copy .env.example .env`), et l'application le redit au démarrage quand
aucune clé n'est posée. Ce fichier déclare cinq réglages : les quatre clés de modèle, et
`LLM_CHAIN`.

Le code en lit **huit**. Sept ne sont écrits nulle part :

    DATABASE_URL            où vivent les données
    FORCE_HTTPS             la redirection HTTPS en production
    LLM_BASE_URL            l'adresse du fournisseur
    LLM_MODEL / LLM_MODELS  le ou les modèles employés
    LUMENIA_DERRIERE_PROXY  comment lire l'adresse du visiteur (anti-spam)
    PUBLIC_ORIGIN           l'adresse publique du site

🔴 ET LE DÉPÔT LE SAVAIT DÉJÀ. Le 18/09, un tour a trouvé que `PUBLIC_ORIGIN` non posée
faisait servir `localhost` dans le `canonical`, l'`og:url`, l'`og:image` et le `Sitemap:`
de robots.txt — un lien partagé qui reste une ligne grise. Le commentaire écrit ce jour-là
dit, mot pour mot : « la variable n'existait que dans ce fichier et dans deux tests ; ni le
README, ni `docker-compose.yml`, ni un `.env.example` ». Le correctif a rendu le produit
capable de deviner l'adresse ; **la variable n'a jamais été déclarée là où quelqu'un la
lirait avant de déployer.**

Une configuration qu'il faut deviner est une configuration qu'on oublie — c'est la phrase
du correctif du 18/09, et elle vaut aussi pour `FORCE_HTTPS`, qui décide si le site
redirige en HTTPS, et pour `LUMENIA_DERRIERE_PROXY`, qui décide si l'anti-spam distingue
deux visiteurs ou les confond tous derrière le proxy.

Ce fichier déduit les variables **depuis le code** — les appels directs et la table
`key_envs`, parce que les clés ne passent pas par `os.getenv` littéral — et exige que
chacune soit déclarée. La prochaine variable ajoutée tombe sous la même règle.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
APP = RACINE / "app"
EXEMPLE = RACINE / ".env.example"

# Lues par le produit mais posées par l'hébergeur ou l'outillage, jamais par ce fichier.
HORS_PERIMETRE = {
    "LLM_API_KEY",   # compatibilité : ancien nom de GEMINI_API_KEY, déclaré par son successeur
}


def _lues_par_le_code() -> set[str]:
    """Toute variable d'environnement que l'application consulte.

    Deux formes, et la seconde est la raison d'être de cette fonction : les clés de modèle
    ne s'écrivent jamais dans un `os.getenv` littéral, elles vivent dans des listes
    `key_envs`. Un crible qui ne verrait que la première conclurait que les quatre clés
    déclarées ne servent à rien — et accuserait le fichier d'être trop large.
    """
    trouvees: set[str] = set()

    for fichier in APP.glob("*.py"):
        source = fichier.read_text(encoding="utf-8-sig")
        trouvees |= set(re.findall(r"getenv\(\s*\"([A-Z_0-9]+)\"", source))
        trouvees |= set(re.findall(r"environ(?:\.get)?\(?\[?\s*\"([A-Z_0-9]+)\"", source))

        arbre = ast.parse(source)
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.keyword) and noeud.arg == "key_envs":
                continue
            if isinstance(noeud, ast.Constant) and noeud.value == "key_envs":
                continue

        for m in re.finditer(r"\"key_envs\"\s*:\s*\[([^\]]*)\]", source):
            trouvees |= set(re.findall(r"\"([A-Z_0-9]+)\"", m.group(1)))

    return trouvees - HORS_PERIMETRE


def _declarees() -> set[str]:
    """Les noms écrits dans `.env.example`, commentés ou non."""
    texte = EXEMPLE.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*#?\s*([A-Z_0-9]{3,})\s*=", texte, re.M))


def test_le_crible_lit_bien_les_deux_formes():
    """Témoin : sans la table `key_envs`, les clés seraient déclarées et jamais vues."""
    lues = _lues_par_le_code()

    assert "LLM_CHAIN" in lues, "la forme directe doit être vue"
    assert "GEMINI_API_KEY" in lues, "et la forme indirecte aussi — sinon ce test accuse à tort"
    assert len(lues) >= 8, sorted(lues)


def test_le_crible_lit_bien_le_fichier_d_exemple():
    """Second témoin : un fichier vide ou déplacé rendrait tout vert sur du vide."""
    assert EXEMPLE.exists(), "le README demande de le copier : il doit exister"
    assert len(_declarees()) >= 5, _declarees()


def test_chaque_variable_lue_est_declaree_dans_l_exemple():
    manquantes = sorted(_lues_par_le_code() - _declarees())

    assert manquantes == [], (
        "ces réglages décident du comportement du produit déployé et ne sont écrits nulle "
        f"part où quelqu'un les lirait avant de déployer — {manquantes}"
    )


def test_l_adresse_publique_et_le_HTTPS_sont_expliques_pas_seulement_nommes():
    """Contrepoids : un nom sans phrase ne se pose pas non plus.

    Les deux réglages qui décident si le site déployé est correct — l'adresse publique et
    la redirection HTTPS — doivent porter, dans ce fichier, de quoi comprendre quand les
    poser. Les lister sans les expliquer ne ferait que déplacer l'oubli.
    """
    # 🔴 PREMIÈRE VERSION : elle regardait une fenêtre de 400 caractères avant la variable.
    # L'en-tête général du bloc y tombait, donc le test restait VERT quand on supprimait
    # l'explication propre à `PUBLIC_ORIGIN`. Il nommait la garantie sans la chercher.
    # Ce qui compte, c'est le commentaire COLLÉ à la ligne : celui qu'on lit en la posant.
    lignes = EXEMPLE.read_text(encoding="utf-8").splitlines()

    for variable in ("PUBLIC_ORIGIN", "FORCE_HTTPS"):
        i = next(n for n, l in enumerate(lignes) if re.match(rf"^\s*#?\s*{variable}\s*=", l))

        juste_au_dessus = []
        for ligne in reversed(lignes[:i]):
            if not ligne.strip().startswith("#"):
                break
            if set(ligne.strip()) <= {"#", "─", " "}:   # une barre de séparation ne dit rien
                break
            juste_au_dessus.append(ligne)

        assert juste_au_dessus, f"{variable} est posée sans un mot d'explication au-dessus"
        assert sum(len(l) for l in juste_au_dessus) > 60, (
            f"{variable} mérite plus qu'un mot : il faut savoir QUAND la poser — {juste_au_dessus}"
        )
