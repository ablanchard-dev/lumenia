# -*- coding: utf-8 -*-
"""Limite de debit sur les seules routes qui appellent un LLM.

Pourquoi elle existe : sans elle, une boucle de dix lignes vide le quota (et le
porte-monnaie) de qui heberge Lumenia. Les routes de lecture ne coutent rien et
ne sont pas rationnees.

Ce qu'elle s'interdit : faire taire le 3114. La reponse 429 porte le numero,
comme le gate d'entree le porte deja. Quelqu'un qui tape trop vite peut etre
quelqu'un qui va mal.
"""
import time

from fastapi.responses import JSONResponse

PAR_MINUTE = 20          # large pour une conversation, etroit pour une boucle
FENETRE = 60.0

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


def client_de(request) -> str:
    entete = request.headers.get("x-forwarded-for")
    if entete:
        return entete.split(",")[0].strip()
    return request.client.host if request.client else "inconnu"


def autorise(cle: str) -> tuple[bool, int]:
    """(passe, secondes avant la prochaine ouverture)."""
    t = maintenant()
    recentes = [v for v in _vues.get(cle, ()) if t - v < FENETRE]
    if len(recentes) >= PAR_MINUTE:
        _vues[cle] = recentes
        return False, max(1, int(FENETRE - (t - recentes[0])) + 1)
    recentes.append(t)
    _vues[cle] = recentes
    return True, 0


def install(app):
    @app.middleware("http")
    async def _anti_spam(request, call_next):
        if request.method == "POST" and request.url.path in ROUTES_LLM:
            passe, attente = autorise(client_de(request))
            if not passe:
                return JSONResponse(
                    {"reply": TROP_VITE, "risk_flag": False, "rate_limited": True},
                    status_code=429,
                    headers={"retry-after": str(attente)},
                )
        return await call_next(request)
