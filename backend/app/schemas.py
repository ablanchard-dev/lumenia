from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ProfileIn(BaseModel):
    low_stim: bool = True
    font_size: int = Field(16, ge=12, le=28)
    pacing: str = "normal"

class DecomposeIn(BaseModel):
    task: str
    steps: int = Field(5, ge=2, le=12)

class ReframeIn(BaseModel):
    thought: str

class CreativityIn(BaseModel):
    goal: str
    mode: str = "ideas"

class ScenarioIn(BaseModel):
    context: str
    style: str = "assertif"

class JournalIn(BaseModel):
    title: str
    content: str

class EntryAssessmentIn(BaseModel):
    answers: Dict[str, int]

class PHQ9In(BaseModel):
    items: List[int]
    item9: Optional[int] = None

class GAD7In(BaseModel):
    items: List[int]

class CoachIn(BaseModel):
    topic: str
    style: str = "brief"

class ChatTurn(BaseModel):
    role: str
    content: str

class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: List[ChatTurn] = []

class EntryVerifyIn(BaseModel):
    challenge_id: str
    answer: str = Field(..., max_length=600)

class EntryStepResult(BaseModel):
    id: str
    dimension: str
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
    results: List[EntryStepResult]
