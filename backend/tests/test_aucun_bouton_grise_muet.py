# -*- coding: utf-8 -*-
"""Un bouton grisé doit dire pourquoi — et par une seule porte.

Mesuré le 17/09/2026 : sur une épreuve à choix multiples, « Valider » est
désactivé tant qu'aucune réponse n'est sélectionnée, sans un mot d'explication.
Même défaut que le « Tout annuler » de DrDXT, corrigé le même jour.

⚠️ Et le même piège, transposé au web : une infobulle `title` sur un bouton
`disabled` **ne s'affiche pas** — le navigateur ne lui envoie pas d'événement de
pointeur. La réponse ne peut donc pas être une infobulle : ce doit être une ligne
**visible**, et tant qu'à faire dans la zone déjà annoncée aux lecteurs d'écran
(`role="status"`), puisque le public visé comprend des personnes qui naviguent
autrement.

La garde ne vérifie pas seulement qu'un message existe : elle impose **une seule
porte**. Griser ce bouton ailleurs qu'au travers de la fonction dédiée serait
rouvrir le défaut en silence.
"""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"
CODE = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


def test_le_bouton_valider_ne_se_grise_que_par_sa_fonction_dediee():
    # Toute ligne qui touche directement `.disabled` de challenge-btn, hors de la
    # fonction dédiée, rouvre le défaut.
    # La seule ligne autorisée est le corps de la fonction dédiée : c'est elle,
    # la porte. Exclure un fichier entier aurait été trop large — on n'exclut
    # qu'une implémentation, nommée.
    PORTE = '$("challenge-btn").disabled = !actif;'
    directes = [
        (i, l.strip()[:90])
        for i, l in enumerate(CODE.splitlines(), 1)
        if not l.strip().startswith("//")
        and l.strip() != PORTE
        and re.search(r'\$\(\s*["\']challenge-btn["\']\s*\)\s*\.disabled\s*=', l)
    ]
    assert directes == [], directes
    assert CODE.count(PORTE) == 1, "la porte doit être unique"


def test_la_fonction_dediee_existe_et_porte_une_raison():
    m = re.search(r"function boutonValider\s*\(([^)]*)\)", CODE)
    assert m, "aucune fonction boutonValider"
    assert "raison" in m.group(1), "la fonction doit accepter la raison du blocage"


def test_le_cas_du_QCM_donne_une_raison_lisible():
    """Le seul cas où le bouton démarre grisé sans action de la personne."""
    assert re.search(r"boutonValider\(\s*false\s*,\s*[\"'][^\"']{15,}", CODE), (
        "le blocage d'un QCM doit être accompagné d'une phrase, pas d'une chaîne vide")


def test_la_raison_est_annoncee_dans_une_zone_vivante():
    """Pour qui n'a pas l'écran sous les yeux, une ligne qui apparaît sans être
    annoncée n'existe pas."""
    assert 'role="status"' in HTML and 'aria-live="polite"' in HTML
