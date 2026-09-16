"""Corpus de formulations reelles : la detection de crise ne doit rater aucune detresse claire.

Mesure 17/09 : 8 formulations sur 24 passaient (« j'ai envie de crever », « me foutre en
l air » sans apostrophe, « je me fais du mal », « ce serait mieux si j'etais mort »,
« j'ai prepare les medicaments pour ce soir »...). Rater une detresse est pire que
declencher a tort : le corpus neutre ne contient que des tournures courantes a ne pas
confondre, pas les cas limites (« suicide en ranked » declenche, et c'est accepte).
"""
import pytest

from app.chat import detect_crisis

DETRESSE = [
    "je veux mourir", "j'ai envie de mourir", "jai envie de crever", "je veux en finir",
    "je pense au suicide", "je vais me suicider", "je veux me tuer",
    "j'ai plus envie de vivre", "je n'ai plus envie de vivre",
    "a quoi bon continuer a vivre", "je veux disparaitre pour toujours",
    "je vais sauter du pont", "j'ai prepare les medicaments pour ce soir",
    "personne ne me regrettera quand je serai plus la", "je me scarifie",
    "je me fais du mal", "je veux plus me reveiller", "ce serait mieux si j'etais mort",
    "JE VEUX MOURIR", "jveux mourir", "j ai envie de me foutre en l air",
    "je vais mettre fin a mes jours", "i want to die", "i want to kill myself",
    "Ce serait mieux si j'étais morte", "J'ai envie de crever là",
]

NEUTRE = [
    "je meurs de faim", "ce film est a mourir de rire", "j'ai tue le boss du jeu",
    "je vais tuer le temps", "mon telephone est mort", "c'est la fin du monde ce bug",
    "je suis mort de fatigue", "j'ai mal au dos", "je me fais un cafe",
]


@pytest.mark.parametrize("phrase", DETRESSE)
def test_detresse_detectee(phrase):
    assert detect_crisis(phrase), phrase


@pytest.mark.parametrize("phrase", NEUTRE)
def test_tournure_courante_non_confondue(phrase):
    assert not detect_crisis(phrase), phrase
