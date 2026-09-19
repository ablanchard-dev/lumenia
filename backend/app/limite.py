# -*- coding: utf-8 -*-
"""Limite de debit sur les seules routes qui appellent un LLM.

Pourquoi elle existe : sans elle, une boucle de dix lignes vide le quota (et le
porte-monnaie) de qui heberge Lumenia. Les routes de lecture ne coutent rien et
ne sont pas rationnees.

Ce qu'elle s'interdit : faire taire le 3114. La reponse 429 porte le numero,
comme le gate d'entree le porte deja. Quelqu'un qui tape trop vite peut etre
quelqu'un qui va mal.
"""
import hashlib
import os
import secrets
import time

from fastapi.responses import JSONResponse

PAR_MINUTE = 20          # large pour une conversation, etroit pour une boucle
FENETRE = 60.0

# 18/09/2026 - La regle annoncee en tete de ce fichier parlait de deux categories : les
# routes qui appellent un modele, et les LECTURES. Le code en laissait passer une
# troisieme -- les ECRITURES. `POST /journal` ecrit en base, ne coute pas un centime de
# quota, et n'etait rationne par rien : 40 requetes d'affilee, 40 fois 200. Une entree
# peut porter 10 000 caracteres ; la borne d'entree limite UNE requete, pas leur nombre,
# et c'est le disque de qui heberge qui se remplit.
#
# Budget separe et plus large : personne qui vide son sac un soir ne doit rencontrer une
# porte fermee. Et c'est la METHODE qui decide, pas une liste ecrite a la main : une route
# d'ecriture ajoutee demain nait protegee.
#
# LE CHIFFRE VIENT D'UNE MESURE, pas d'un gout : la rafale legitime la plus dense du
# produit est le parcours d'entree -- 30 `/entry/verify` plus un `/entry/complete`, soit
# 31 ecritures qu'un candidat rapide enchaine en moins d'une minute. Un premier essai a
# 60 a d'ailleurs fait rougir `test_chat_is_gated_server_side_until_entry_passed`, qui
# joue trois parcours d'affilee : c'est la suite qui a dit que le budget etait trop etroit.
# 120 laisse donc quatre parcours de marge.
#
# CE QUE CA NE FAIT PAS : arreter quelqu'un de determine. 120 ecritures par minute restent
# des donnees. Ce que ca arrete, c'est la boucle -- celle qui ecrirait des milliers de fois
# par seconde. Un plafond en OCTETS serait la reponse complete ; il n'est pas ecrit ici.
PAR_MINUTE_ECRITURE = 120
ECRITURES = {"POST", "PUT", "PATCH", "DELETE"}

# 19/09/2026 - LE NUMERO MANQUAIT ICI, et c'etait le pire endroit possible. Ce refus-la
# tombe dans le middleware, AVANT que la route ne s'execute -- donc avant `_guard(...)`,
# le garde de crise que `POST /journal` fait passer sur le titre et le contenu. Ecrire sa
# detresse dans son journal ramene le 3114 ; l'ecrire une fois de trop ne le ramenait pas.
# C'etait la seule reponse du produit ou personne ne rattrapait la detresse, et trois
# documents plus un test promettaient deja le contraire.
TROP_D_ECRITURES = (
    "Trop d'enregistrements d'affilee : ca repart dans une minute. "
    "Rien n'est perdu, et rien ne t'est reproche.\n\n"
    "Si ca urge, le **3114** (national, gratuit, 24h/24) repond tout de suite, "
    "et le **15** pour une urgence medicale."
)

# 18/09/2026 - LE JUGE DU PARCOURS D'ENTREE. La regle en tete de ce fichier dit « les
# seules routes qui appellent un LLM ». Il en manquait une, et pas dans la liste : dans le
# chemin. `POST /entry/verify` -> `verify_challenge` -> `_chat` : une epreuve `objective`
# (117 items de la banque) dont la formulation n'est pas dans la liste de synonymes part
# chez le modele. La route tombait donc dans le budget des ECRITURES -- 120/min, calibre
# sur le DISQUE, pas sur le quota -- soit six fois le plafond de conversation pour un appel
# qui coute exactement pareil.
#
# Le plafond est GLOBAL au processus, et c'est voulu : ce qu'on protege ici est le quota de
# qui heberge Lumenia, et un quota n'a pas d'adresse IP. Un plafond par visiteur laisse N
# visiteurs multiplier la facture par N.
#
# Au-dela, `verify_challenge` rend `undetermined` : l'etat que le produit sait deja tenir
# (« juge injoignable, epreuve NON JUGEE »). Rendre « faux » ferait echouer un candidat
# valable parce que quelqu'un d'autre a boucle sur la route une minute plus tot.
#
# 60 : le double d'un parcours entier (30 epreuves) integralement juge, ce qui n'arrive
# jamais -- la moitie du tirage est en QCM et la liste de synonymes absorbe l'essentiel du
# reste.
PAR_MINUTE_JUGE = 60

CLE_DU_JUGE = "juge-entree"

# Les routes qui ATTEIGNENT le modele sans passer par le budget du middleware. Une seule
# a ce jour, et elle n'est pas une exception de confort : son plafond est plus strict que
# celui des routes de conversation (global, pas par visiteur). Toute entree ajoutee ici
# doit venir avec un test qui EPUISE son plafond -- sinon la derogation ne garde rien.
ROUTES_LLM_RATIONNEES_AILLEURS = {"/entry/verify"}


def juge_autorise() -> bool:
    """Le juge d'entree peut-il encore partir chez le modele dans cette fenetre ?"""
    passe, _ = autorise(CLE_DU_JUGE, PAR_MINUTE_JUGE)
    return passe


ROUTES_LLM = {
    "/chat",
    "/focus/decompose",
    "/impostor/reframe",
    "/creativity/generate",
    "/scenarios",
    "/psy/coach",
}

TROP_VITE = (
    "Trop de messages d'affilee : je reprends dans une minute. "
    "Ce n'est pas un refus, c'est une limite technique.\n\n"
    "Si ca urge, le **3114** (national, gratuit, 24h/24) repond tout de suite, "
    "et le **15** pour une urgence medicale."
)

# ponytail: compteurs en memoire, un seul processus. Si Lumenia passe a plusieurs
# instances, la limite devient par instance -- il faudra un compteur partage.
_vues: dict[str, list[float]] = {}
_decalage = 0.0


def maintenant() -> float:
    return time.monotonic() + _decalage


def avancer(secondes: float) -> None:
    """Deplace l'horloge : les tests n'ont pas a attendre une vraie minute."""
    global _decalage
    _decalage += secondes


def reset() -> None:
    global _decalage
    _vues.clear()
    _decalage = 0.0


# Le limiteur n'a jamais eu besoin de SAVOIR qui vient : il lui faut une cle stable
# le temps d'une fenetre d'une minute. Une adresse IP est une donnee personnelle
# (CJUE, Breyer, C-582/14) et Lumenia est une appli de sante mentale : garder
# l'adresse en clair, c'est relier quelqu'un aux minutes exactes ou il a ecrit a un
# compagnon de crise. Le sel est tire au demarrage et ne quitte jamais le processus :
# la cle n'est donc reversible ni en memoire, ni d'un redemarrage a l'autre.
_SEL = secrets.token_bytes(32)


def cle_de(adresse: str) -> str:
    """Condensat sale de l'adresse : distingue les visiteurs sans les nommer."""
    return hashlib.blake2b(adresse.encode("utf-8"), key=_SEL, digest_size=16).hexdigest()


def reinitialiser() -> None:
    """Meme geste que `reset`, sous le nom qu'emploient les tests de vie privee."""
    reset()


def derriere_un_proxy() -> bool:
    """Un proxy a-t-il ete DECLARE devant Lumenia ?

    `x-forwarded-for` est ecrit par le client : le lire sans proxy declare, c'est
    laisser n'importe qui repartir de zero en incrementant un en-tete -- la limite
    ne protege alors plus rien. Derriere un hebergeur qui met un proxy (Render,
    Fly...), l'inverse est vrai : tout arrive avec la meme IP de sortie, et sans
    l'en-tete un visiteur bruyant fermerait la porte a tous les autres.
    Les deux modes sont justes ; c'est celui qui heberge qui sait lequel s'applique.
    """
    return os.getenv("LUMENIA_DERRIERE_PROXY", "").strip().lower() in {"1", "true", "oui", "yes"}


def client_de(request) -> str:
    if derriere_un_proxy():
        entete = request.headers.get("x-forwarded-for")
        if entete:
            return entete.split(",")[0].strip()
    return request.client.host if request.client else "inconnu"


def _oublier_les_perimes(t: float) -> None:
    """Une entree dont la fenetre est passee n'apprend plus rien : elle part.

    Sans ca, chaque client vu une fois reste en memoire pour toujours -- et derriere un
    proxy declare, une boucle qui incremente `x-forwarded-for` fait monter cette memoire
    jusqu'a faire tomber le serveur. Le balayage ne se declenche qu'au-dessus du seuil :
    il ne coute rien tant que Lumenia ne voit que ses visiteurs reels.
    """
    for cle in [c for c, vues in _vues.items() if all(t - v >= FENETRE for v in vues)]:
        del _vues[cle]


# ponytail: balayage au seuil plutot qu'une tache de fond. Une tache de fond serait un
# processus de plus a surveiller pour un dict qui tient dans une poignee de Ko.
VISITEURS_AVANT_BALAYAGE = 1000


def autorise(cle: str, plafond: int = PAR_MINUTE) -> tuple[bool, int]:
    """(passe, secondes avant la prochaine ouverture)."""
    t = maintenant()
    if len(_vues) > VISITEURS_AVANT_BALAYAGE:
        _oublier_les_perimes(t)
    recentes = [v for v in _vues.get(cle, ()) if t - v < FENETRE]
    if len(recentes) >= plafond:
        _vues[cle] = recentes
        return False, max(1, int(FENETRE - (t - recentes[0])) + 1)
    recentes.append(t)
    _vues[cle] = recentes
    return True, 0


def install(app):
    @app.middleware("http")
    async def _anti_spam(request, call_next):
        if request.method in ECRITURES:
            cle = cle_de(client_de(request))
            if request.url.path in ROUTES_LLM:
                passe, attente = autorise(cle, PAR_MINUTE)
                if not passe:
                    return JSONResponse(
                        {"reply": TROP_VITE, "risk_flag": False, "rate_limited": True},
                        status_code=429,
                        headers={"retry-after": str(attente)},
                    )
            else:
                # Budget separe : une ecriture ne consomme pas le quota de conversation,
                # et inversement. La cle est prefixee, donc les deux compteurs ne se
                # melangent pas pour un meme visiteur.
                passe, attente = autorise("ecriture:" + cle, PAR_MINUTE_ECRITURE)
                if not passe:
                    return JSONResponse(
                        {"detail": TROP_D_ECRITURES, "rate_limited": True},
                        status_code=429,
                        headers={"retry-after": str(attente)},
                    )
        return await call_next(request)
