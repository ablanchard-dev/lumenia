# -*- coding: utf-8 -*-
"""Vérifie la VÉRACITÉ de la banque d'entrée.

Pour chaque question dont la réponse est calculable (suites, arithmétique, jours,
logique), on RECALCULE la bonne réponse de façon indépendante, puis on confirme
qu'elle est bien acceptée par les réponses stockées — via la vraie fonction de
matching `_matches` de l'app. Contrôles structurels en plus (ids uniques, champs).

Lancement : depuis backend/  ->  .venv\\Scripts\\python.exe _verify_bank.py
Doit afficher "TOUT EST VRAI" et sortir en code 0.
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows -> UTF-8
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))
from app.entry import _matches  # vraie logique de validation de l'app

BANK = json.loads((Path(__file__).parent / "app" / "entry_bank.json").read_text(encoding="utf-8"))
BY_ID = {item["id"]: {**item, "dimension": dim["dimension"], "kind": dim["kind"]}
         for dim in BANK for item in dim["pool"]}

DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def shift(day, delta):
    return DAYS[(DAYS.index(day) + delta) % 7]


def is_prime(n):
    return n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1))


def next_prime(n):
    n += 1
    while not is_prime(n):
        n += 1
    return n


def escargot():  # mur 10 m, +3 le jour, -2 la nuit
    pos, day = 0, 0
    while True:
        day += 1
        pos += 3
        if pos >= 10:
            return day
        pos -= 2


def fratrie():  # Léo (G): freres=B-1=soeurs=F ; Jade (F): freres=B=2*(soeurs=F-1)
    for B in range(1, 12):
        for F in range(1, 12):
            if B - 1 == F and B == 2 * (F - 1):
                return B + F
    return None


def poignees(n):  # combinaisons de paires
    return n * (n - 1) // 2


# --- réponses RECALCULÉES indépendamment ---
computed = {
    "suite": 17 * 2 - 1,            # rule ×2−1
    "suite_pas": 13 + 5,            # +1,+2,+3,+4,+5
    "fibo": 5 + 8,                  # Fibonacci
    "suite_premiers": next_prime(11),
    "suite_carres": 6 ** 2,
    "marquepage": (11 - 10) / 2,    # b+p=11, b=p+10 -> p=0.5
    "machines": 5,                  # 1 machine -> 1 piece en 5 min
    "nenuphar": 48 - 1,
    "fratrie": fratrie(),
    "escargot": escargot(),
    "chaussettes": 2 + 1,           # 2 couleurs -> +1
    "prix_remise": 80 * (1 - 0.25),
    "age_double": 34 - 2 * 8,       # 34 + x = 2(8 + x)  ->  x = 18
    "poignees_main": poignees(5),
    "suite_x3": 54 * 3,              # ×3 -> 162
    "suite_alt": 16 + 6,            # +1,+2,+3,+4,+5,+6 -> 22
    "trois_chats": 3,               # 1 chat -> 1 souris/3 min ; 100 souris/100 min -> 3 chats
    "douzaine_demi": (6 // 2) + 2,  # moitie de 6 = 3, +2 -> 5
    "minutes_heures": 24 * 60 // 4,  # quart de journee -> 360 min
    "suite_moins": 8 // 2,           # ÷2 -> 4
    "suite_fact": 120 * 6,           # ×2,×3,...,×6 -> 720
    "train_vitesse": 60 * 60 // 45,  # 60 km / 45 min -> 80 km/h
    "bonbons_partage": (24 // 6) + (2 * (24 // 6)) // 4,  # 4 + 2 -> 6
    "double_moitie": (30 - 10) // 2,  # 2x+10=30 -> x=10
    # jours
    "jours": shift("samedi", 2 + 1),     # avant-hier=samedi -> demain
    "jours_2": shift("vendredi", -3 - 1),  # today+3=vendredi -> hier
}

# --- réponses logiques/verbales (vérifiées par raisonnement) ---
verbal = {
    "zorg": "non",               # chanteurs bleus pas forcément Zorgs
    "syllogisme_roses": "non",   # fleurs qui fanent pas forcément des roses
    "syllogisme_chats": "non",   # aucun animal ne parle, le chat est un animal -> non
    "grandeur": "lea",           # Lea > Zoe > Marie
    "ordre_taille": "sam",       # Tom > Lina > Sam (vitesse) -> plus lent = Sam
}


def check(qid, correct):
    item = BY_ID.get(qid)
    if not item:
        return False, f"{qid} introuvable"
    ok = any(_matches(acc, str(correct)) for acc in item.get("answers", []))
    return ok, f"{qid:16} calc={str(correct):<8} {'OK' if ok else 'REFUSE par ' + str(item.get('answers'))}"


def main():
    errors = []

    # 1) structure
    ids = [item["id"] for dim in BANK for item in dim["pool"]]
    dups = {i for i in ids if ids.count(i) > 1}
    if dups:
        errors.append(f"ids dupliques: {dups}")
    for dim in BANK:
        for item in dim["pool"]:
            if not item.get("question", "").strip():
                errors.append(f"{item.get('id')} : question vide")
            if dim["kind"] == "objective" and not item.get("answers"):
                errors.append(f"{item['id']} : pas de reponses (objective)")

    print("=== Comptage par dimension ===")
    for dim in BANK:
        print(f"  {dim['dimension']:12} {dim['kind']:9} pool={len(dim['pool'])}")
    print(f"  TOTAL = {len(ids)} questions\n")

    print("=== Réponses recalculées (auto) ===")
    for qid, val in {**computed, **verbal}.items():
        ok, msg = check(qid, val)
        print(("  [OK]  " if ok else "  [!!] ") + msg)
        if not ok:
            errors.append(msg)

    # items objectifs verbaux (devinettes) non calculables -> listés pour info
    auto = set(computed) | set(verbal)
    verbal_riddles = [i for i, it in BY_ID.items()
                      if it["kind"] == "objective" and i not in auto]
    print("\n=== Devinettes verbales (véracité validée manuellement) ===")
    print("  " + ", ".join(sorted(verbal_riddles)))

    print()
    if errors:
        print("ÉCHEC — problèmes détectés :")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"TOUT EST VRAI ✓  ({len(computed) + len(verbal)} réponses recalculées validées, "
          f"{len(verbal_riddles)} devinettes verbales, {len(ids)} questions au total)")


if __name__ == "__main__":
    main()
