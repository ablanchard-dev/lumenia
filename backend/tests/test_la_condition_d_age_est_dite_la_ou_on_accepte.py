# -*- coding: utf-8 -*-
"""La condition d'âge doit être vraie, et dite là où la personne accepte.

18/09/2026. Les CGU posent une condition d'accès :

    « L'accès est réservé aux personnes d'au moins 16 ans, âge du consentement
      numérique en France. »

**Deux défauts, mesurés.**

1. La justification est fausse. En France, l'âge du consentement numérique est
   **15 ans**, pas 16 : le RGPD (art. 8) laisse chaque État choisir entre 13 et
   16, et la loi Informatique et Libertés retient 15. Source : CNIL,
   « Rechercher le consentement d'un parent pour les mineurs de moins de 15 ans »
   (cnil.fr, lu le 18/09/2026). Exiger 16 ans reste le droit du service — c'est
   l'argument juridique qui était faux, et un chiffre de loi cité de travers sur
   une page de CGU n'est pas un détail de rédaction.

2. L'écran de consentement — le seul endroit où quelqu'un coche « j'ai compris et
   j'accepte ces conditions » — ne mentionnait **pas** l'âge. Les trois points
   listés étaient les données, le non-dispositif-médical et le 3114. Une personne
   de quatorze ans acceptait donc sans jamais rencontrer la condition censée la
   concerner. La condition vivait sur une page légale que l'on atteint par un
   lien de pied de page.

Ce test tient les deux : le chiffre de la loi ne doit pas être écrit faux, et la
condition doit exister là où on accepte.
"""
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CGU = RACINE / "static" / "cgu.html"
ACCUEIL = RACINE / "static" / "index.html"

# L'age retenu par la France, art. 45 de la loi Informatique et Libertes.
CONSENTEMENT_NUMERIQUE_FR = 15


def _texte(fichier: Path) -> str:
    return " ".join(fichier.read_text(encoding="utf-8").split())


def _bloc_du_consentement() -> str:
    """Le seul endroit ou la personne coche « j'accepte »."""
    html = _texte(ACCUEIL)
    debut = html.find('id="screen-consent"')
    assert debut != -1, "l'ecran de consentement a disparu de l'accueil"
    fin = html.find("</section>", debut)
    return html[debut:fin]


def test_le_crible_lit_bien_les_deux_surfaces():
    """Témoin : sans lui, un fichier déplacé rendrait tout vert sur du vide."""
    bloc = _bloc_du_consentement()

    assert "j'accepte" in bloc.lower(), "le crible ne lit plus le bloc d'acceptation"
    assert "16" in _texte(CGU), "les CGU n'annoncent plus de seuil d'age"


def test_les_cgu_n_attribuent_pas_a_la_france_un_age_qu_elle_ne_retient_pas():
    cgu = _texte(CGU)

    fautif = re.search(
        r"(\d{2})\s*ans[^.]{0,80}?consentement\s+num[ée]rique\s+en\s+France", cgu
    )
    if fautif:
        assert int(fautif.group(1)) == CONSENTEMENT_NUMERIQUE_FR, (
            f"les CGU presentent {fautif.group(1)} ans comme « l'age du consentement "
            f"numerique en France » ; la France retient {CONSENTEMENT_NUMERIQUE_FR} ans "
            "(RGPD art. 8 + loi Informatique et Libertes, source CNIL). Exiger un seuil "
            "plus haut est permis — l'annoncer comme la loi ne l'est pas"
        )


def test_la_condition_d_age_est_rappelee_la_ou_on_coche():
    bloc = _bloc_du_consentement()

    assert re.search(r"\b16\s*(&nbsp;)?ans\b", bloc), (
        "l'ecran de consentement ne dit pas la condition d'age. La case cochee annonce "
        "« j'ai compris et j'accepte ces conditions » — une condition qui ne figure que "
        "sur une page atteinte par un lien de pied de page n'est pas rencontree par qui "
        "accepte"
    )


def test_l_ecran_renvoie_toujours_aux_cgu_completes():
    """Le rappel court ne remplace pas le texte : le lien doit rester."""
    bloc = _bloc_du_consentement()

    assert '/cgu' in bloc, "l'ecran de consentement ne renvoie plus aux conditions completes"
