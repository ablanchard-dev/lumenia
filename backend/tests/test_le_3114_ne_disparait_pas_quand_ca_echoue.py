# -*- coding: utf-8 -*-
"""Le numéro doit être là où la personne est, y compris quand le produit échoue.

18/09/2026. `test_le_3114_est_toujours_atteignable.py` compte les occurrences sur
la page entière (« au moins quatre »). C'est vrai, et ça ne dit pas **où** :
mesuré aujourd'hui, l'écran des épreuves d'entrée n'en portait aucune, et les
quatre messages d'erreur affichés par le script n'en portaient aucune non plus.

Deux moments concrets où le numéro manquait :

- quelqu'un bloqué sur une épreuve d'entrée, avec « Erreur de connexion au
  serveur » sous les yeux, n'avait le numéro nulle part sur cet écran ;
- dans le chat, la bannière de sécurité est `hidden` tant qu'aucun risque n'est
  détecté : quand l'envoi échoue, le message d'excuse était le seul texte neuf à
  l'écran, et il ne portait pas le numéro.

C'est le même défaut que la réponse 500 du serveur, vu du côté navigateur : la
garantie tient quand tout va bien, et lâche au moment où elle compte.
"""
import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
HTML = (RACINE / "static" / "index.html").read_text(encoding="utf-8")
JS = (RACINE / "static" / "app.js").read_text(encoding="utf-8")

# Les écrans où l'on SÉJOURNE. Le splash est une porte d'une seconde avec un seul
# bouton : son cas est couvert par la règle sur les messages d'erreur ci-dessous.
ECRANS_HABITES = ("screen-consent", "screen-challenge", "screen-fail", "screen-chat")


def _bloc_ecran(identifiant: str) -> str:
    debut = HTML.index(f'id="{identifiant}"')
    suivants = [m.start() for m in re.finditer(r'id="screen-[^"]+"', HTML) if m.start() > debut]
    return HTML[debut: suivants[0] if suivants else len(HTML)]


def _messages_d_erreur_du_script() -> list[str]:
    """Les phrases que le script affiche quand une requête échoue.

    23/09/2026 : elles vivent toutes dans `panne(err)` (une phrase par panne) ; avant, chaque
    `catch` écrivait la sienne et on les retrouvait au mot « serveur ». Le crible lit donc le
    corps de `panne`, en y ajoutant le complément `TOUJOURS_3114` qu'elle colle à chaque phrase
    qui n'a pas déjà le numéro.
    """
    corps = JS[JS.index("function panne("):]
    corps = corps[: corps.index("\n  }\n")]
    # Les littéraux lus DANS L'ORDRE (un `""` vide compte pour une paire) : un simple
    # `"[^"]+"` appariait les guillemets de travers et collait du code dans les « phrases ».
    phrases = [t for t in re.findall(r'"((?:[^"\\\n]|\\.)*)"', corps) if len(t) >= 12 and " " in t]
    complement = re.search(r'const TOUJOURS_3114 = "([^"]+)"', JS)
    colle = "TOUJOURS_3114" in corps and complement is not None
    return [p if "3114" in p or not colle else p + " " + complement.group(1) for p in phrases]


def test_le_crible_voit_bien_les_messages_d_erreur():
    """Témoin : un motif cassé rendrait le test suivant vert sur le vide."""
    messages = _messages_d_erreur_du_script()

    assert len(messages) >= 4, messages
    assert any("réseau" in m for m in messages)


@pytest.mark.parametrize("ecran", ECRANS_HABITES)
def test_chaque_ecran_habite_porte_le_numero(ecran):
    bloc = _bloc_ecran(ecran)

    assert "3114" in bloc, (
        f"{ecran} ne porte pas le 3114 : quelqu'un qui reste bloqué là n'a aucun "
        "numéro sous les yeux"
    )


def test_chaque_message_d_erreur_porte_le_numero():
    muets = [m for m in _messages_d_erreur_du_script() if "3114" not in m]

    assert muets == [], (
        "ces messages annoncent un échec sans donner le numéro. Dans le chat, la "
        "bannière de sécurité est masquée tant qu'aucun risque n'est détecté : le "
        f"message d'échec est alors le seul texte neuf à l'écran — {muets}"
    )


def test_le_numero_du_chat_ne_depend_pas_de_la_banniere_masquee():
    """La garantie positive : le chat garde le numéro visible au repos, sans quoi
    tout reposerait sur une bannière qui n'apparaît qu'après coup."""
    chat = _bloc_ecran("screen-chat")
    sans_caches = re.sub(r"<(\w+)[^>]*\shidden[^>]*>.*?</\1>", "", chat, flags=re.S)

    assert sans_caches.count("3114") >= 1
