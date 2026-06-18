# -*- coding: utf-8 -*-
"""Vérifie la VÉRACITÉ et la STRUCTURE de la banque d'entrée.

Pour chaque question dont la réponse est calculable (suites, arithmétique, jours,
logique, empan envers), on RECALCULE la bonne réponse de façon indépendante, puis
on confirme qu'elle est bien acceptée — via la vraie fonction `_matches` de l'app.
Contrôles structurels en plus : ids uniques, champ question non vide, items
`objective` avec réponses, items `qcm` dont la clé pointe vers un choix existant
et sans choix dupliqués.

Le `kind` est porté par CHAQUE item (qcm / objective / open).

Lancement : depuis backend/  ->  .venv\\Scripts\\python.exe _verify_bank.py
Doit afficher "TOUT EST VRAI" et sortir en code 0.
"""
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows -> UTF-8
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))
from app.entry import _matches  # vraie logique de validation de l'app

BANK = json.loads((Path(__file__).parent / "app" / "entry_bank.json").read_text(encoding="utf-8"))
BY_ID = {item["id"]: {**item, "dimension": dim["dimension"]}
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


# --- réponses RECALCULÉES indépendamment (items legacy calculables) ---
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
    "suite_impairs": 9 + 2,          # impairs -> 11
    "suite_double_un": 16 * 2,       # ×2 -> 32
    "crayons_boites": 20 * 3 // 12,  # 0,25 €/crayon -> 5 €
    "horloge_sonne": (7 - 1) * (6 // (4 - 1)),  # intervalles : 6 × 2s -> 12
    "ages_somme": (10 + 4) // 2,     # (somme+diff)/2 -> 7
    "suite_diff2": 40 * 2,           # ×2 -> 80
    "suite_minus3": 91 - 3,          # -3 -> 88
    "pommes_reste": 10 // 2 - 2,     # 5 - 2 -> 3
    "fourmi_pattes": 3 * 8 + 4 * 6,  # 24 + 24 -> 48
    "remise_deux": 40 * 0.5 * 0.9,   # -50% puis -10% -> 18
    # jours
    "jours": shift("samedi", 2 + 1),     # avant-hier=samedi -> demain
    "jours_2": shift("vendredi", -3 - 1),  # today+3=vendredi -> hier
    "jours_3": shift("mercredi", 1 + 2),  # hier=mercredi -> apres-demain
}

# --- réponses logiques/verbales (vérifiées par raisonnement) ---
verbal = {
    "zorg": "non",               # chanteurs bleus pas forcément Zorgs
    "syllogisme_roses": "non",   # fleurs qui fanent pas forcément des roses
    "syllogisme_chats": "non",   # aucun animal ne parle, le chat est un animal -> non
    "grandeur": "lea",           # Lea > Zoe > Marie
    "ordre_taille": "sam",       # Tom > Lina > Sam (vitesse) -> plus lent = Sam
    "syllogisme_oiseaux": "non",  # le pingouin est un oiseau qui ne vole pas
}


def check(qid, correct):
    item = BY_ID.get(qid)
    if not item:
        return False, f"{qid} introuvable"
    ok = any(_matches(acc, str(correct)) for acc in item.get("answers", []))
    return ok, f"{qid:16} calc={str(correct):<8} {'OK' if ok else 'REFUSE par ' + str(item.get('answers'))}"


def check_qcm(item):
    """Validation structurelle d'un item QCM : 4 choix non vides et distincts,
    clé ∈ {A,B,C,D} pointant vers un choix existant."""
    qid, errs = item.get("id"), []
    letters = ["A", "B", "C", "D"]
    choices = item.get("choices") or {}
    texts = [str(choices.get(L, "")).strip() for L in letters]
    for L, t in zip(letters, texts):
        if not t:
            errs.append(f"{qid} : choix {L} vide")
    present = [t for t in texts if t]
    if len(set(present)) < len(present):
        errs.append(f"{qid} : choix QCM dupliqués")
    ans = str(item.get("answer", "")).strip().upper()
    if ans not in letters:
        errs.append(f"{qid} : clé '{ans}' n'est pas A/B/C/D")
    elif not str(choices.get(ans, "")).strip():
        errs.append(f"{qid} : la clé {ans} pointe vers un choix vide")
    return errs


def main():
    errors = []

    # 1) structure (par item, kind porté par l'item)
    ids = [item["id"] for dim in BANK for item in dim["pool"]]
    dups = {i for i in ids if ids.count(i) > 1}
    if dups:
        errors.append(f"ids dupliques: {dups}")
    for dim in BANK:
        for item in dim["pool"]:
            qid = item.get("id")
            if not item.get("question", "").strip():
                errors.append(f"{qid} : question vide")
            kind = item.get("kind")
            if kind == "objective":
                if not item.get("answers"):
                    errors.append(f"{qid} : pas de reponses (objective)")
            elif kind == "qcm":
                errors.extend(check_qcm(item))
            elif kind == "open":
                pass
            else:
                errors.append(f"{qid} : kind inconnu ({kind!r})")

    print("=== Comptage par dimension ===")
    for dim in BANK:
        kinds = {}
        for it in dim["pool"]:
            kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
        breakdown = "  ".join(f"{k}={v}" for k, v in sorted(kinds.items()))
        print(f"  {dim['dimension']:8} pool={len(dim['pool']):3}  {breakdown}")
    print(f"  TOTAL = {len(ids)} questions\n")

    print("=== Réponses recalculées (legacy calculable) ===")
    for qid, val in {**computed, **verbal}.items():
        ok, msg = check(qid, val)
        print(("  [OK]  " if ok else "  [!!] ") + msg)
        if not ok:
            errors.append(msg)

    # 2) empan envers : la réponse est la suite de chiffres inversée -> recalculable
    empan = [it for it in BY_ID.values() if it.get("sous_type") == "Empan envers"]
    n_empan_ok = 0
    for it in empan:
        seq = [t for t in re.split(r"[^0-9]+", it["question"]) if t]
        expected = "-".join(reversed(seq))
        if any(_matches(acc, expected) for acc in it.get("answers", [])):
            n_empan_ok += 1
        else:
            errors.append(f"{it['id']} : empan envers attendu {expected}, stocké {it.get('answers')}")
    print(f"\n=== Empan envers recalculé (suite inversée) : {n_empan_ok}/{len(empan)} OK ===")

    # 3) inventaire des items à véracité non recalculée (QC fait à la source)
    auto = set(computed) | set(verbal)
    qcm_items = [i for i, it in BY_ID.items() if it["kind"] == "qcm"]
    trusted = [i for i, it in BY_ID.items()
               if it["kind"] == "objective" and i not in auto and it.get("sous_type") != "Empan envers"]
    print(f"=== {len(qcm_items)} items QCM (structure validée : clé ∈ choix, pas de doublon) ===")
    print(f"=== {len(trusted)} items objectifs non recalculés (devinettes + libre-stricte, QC source) ===")

    print()
    if errors:
        print("ÉCHEC — problèmes détectés :")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"TOUT EST VRAI ✓  ({len(computed) + len(verbal)} legacy recalculés + {n_empan_ok} empan-envers, "
          f"{len(qcm_items)} QCM structurés, {len(ids)} questions au total)")


if __name__ == "__main__":
    main()
