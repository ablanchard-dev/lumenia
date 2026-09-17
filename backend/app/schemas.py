from pydantic import BaseModel, Field
from typing import Annotated, List, Optional, Dict

# --- Bornes ---------------------------------------------------------------
# Deux raisons, mesurees le 17/09/2026 :
#
# 1. Un questionnaire clinique TRONQUE ressortait rassurant : `phq9_score([0,0,0])`
#    rendait « minimal, aucun risque ». Le PHQ-9 a exactement 9 items cotes 0 a 3,
#    le GAD-7 en a 7. Hors de ces bornes ce n'est pas un score bas, c'est PAS un
#    score -- et un verdict tranquillisant sur un questionnaire incomplet est
#    exactement ce qu'un outil de sante mentale ne doit jamais produire.
#
# 2. Aucun texte parti vers le modele n'etait borne : une seule requete pouvait
#    porter des megaoctets, factures a qui heberge Lumenia. La limite de debit
#    compte les appels, pas leur taille.
#
# Les plafonds de texte sont larges a dessein : ils arretent l'abus, pas l'usage.
Cotation = Annotated[int, Field(ge=0, le=3)]          # echelle Likert des deux questionnaires
TexteCourt = Annotated[str, Field(max_length=2_000)]   # ce qu'on ecrit dans un champ
TexteLong = Annotated[str, Field(max_length=10_000)]   # une entree de journal


class ProfileIn(BaseModel):
    low_stim: bool = True
    font_size: int = Field(16, ge=12, le=28)
    pacing: str = Field("normal", max_length=40)

class DecomposeIn(BaseModel):
    task: TexteCourt
    steps: int = Field(5, ge=2, le=12)

class ReframeIn(BaseModel):
    thought: TexteCourt

class CreativityIn(BaseModel):
    goal: TexteCourt
    mode: str = Field("ideas", max_length=40)

class ScenarioIn(BaseModel):
    context: TexteCourt
    style: str = Field("assertif", max_length=40)

class JournalIn(BaseModel):
    title: Annotated[str, Field(max_length=200)]
    content: TexteLong

class EntryAssessmentIn(BaseModel):
    # Le parcours compte six dimensions ; 60 entrees laissent toute la marge utile.
    # On borne la TAILLE, pas le sens : la liste legitime des cles de cette route
    # heritee n'est pas connue, donc elle ne s'invente pas ici.
    answers: Annotated[
        Dict[Annotated[str, Field(max_length=60)], int],
        Field(max_length=60),
    ]

class PHQ9In(BaseModel):
    # Exactement 9 items cotes 0-3 : ni 8 ni 10, et rien hors de l'echelle.
    items: Annotated[List[Cotation], Field(min_length=9, max_length=9)]
    item9: Optional[Cotation] = None

class GAD7In(BaseModel):
    items: Annotated[List[Cotation], Field(min_length=7, max_length=7)]

class CoachIn(BaseModel):
    topic: TexteCourt
    style: str = Field("brief", max_length=40)

class ChatTurn(BaseModel):
    role: str = Field(..., max_length=20)
    content: str = Field(..., max_length=4_000)

class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    # Seuls les derniers tours atteignent le modele, mais le corps entier est lu
    # et analyse avant : la borne doit etre au bord, pas apres.
    history: Annotated[List[ChatTurn], Field(max_length=100)] = []

class EntryVerifyIn(BaseModel):
    challenge_id: str = Field(..., max_length=120)
    answer: str = Field(..., max_length=600)

class EntryStepResult(BaseModel):
    id: str = Field(..., max_length=120)
    dimension: str = Field(..., max_length=60)
    ok: bool
    answer: str = Field("", max_length=600)
    attempts: int = 1
    skipped: bool = False
    # `/entry/verify` sait déjà distinguer « réponse fausse » de « juge injoignable »
    # (il renvoie `undetermined`). Ce drapeau s'arrêtait au front : le serveur ne
    # voyait qu'un `ok=False` et annonçait un échec au parcours. Avec ~14,65 items
    # jugés sur 30 et 4 erreurs permises, une panne de juge rendait le parcours
    # quasi impassable — et disait à la personne qu'elle avait échoué un test
    # cognitif. Défaut par défaut à False : les clients existants ne changent pas.
    undetermined: bool = False

class EntryCompleteIn(BaseModel):
    # 30 epreuves au parcours : une liste de 10 000 resultats n'est pas un parcours.
    results: Annotated[List[EntryStepResult], Field(max_length=60)]
