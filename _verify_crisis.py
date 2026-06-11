# -*- coding: utf-8 -*-
"""Vérifie le lexique de détection de crise : signaux forts captés, innocents ignorés."""
import sys
sys.path.insert(0, r"C:/Users/blanc/Downloads/LUMENIA_MVP_SCALE_v2_1_FIX2/backend")
from app.chat import detect_crisis

# (phrase, attendu)
TESTS = [
    # — doivent déclencher —
    ("je veux me suicider", True),
    ("envie de mourir", True),
    ("idées noires", True),
    ("I want to die", True),
    ("I want to kill myself", True),
    ("sui cide", True),
    ("je veux crever", True),
    ("je veux mourir", True),
    ("je vais me pendre ce soir", True),
    ("je vais sauter du pont", True),
    ("je pense à sauter par la fenetre", True),
    ("j'ai avale toutes mes pilules pour ne plus me reveiller", True),
    ("plus la force de continuer, je veux que ca s'arrete pour toujours", True),
    ("je vais mettre fin à ma vie", True),
    ("je veux me foutre en l'air", True),
    ("I'm going to end my life", True),
    ("sometimes I think I'd be better off dead", True),
    ("je veux plus jamais me reveiller", True),
    # — ne doivent PAS déclencher (faux positifs anxiogènes) —
    ("j'ai sauté du lit ce matin", False),
    ("ce projet me tue le cerveau", False),
    ("j'ai avalé un cachet pour la migraine", False),
    ("je vais tuer le temps avant le rendez-vous", False),
    ("cette série est à mourir de rire", False),
    ("j'ai raté mon examen et je suis dégouté", False),
    ("je suis crevé, je vais dormir", False),
]

fails = 0
for phrase, expected in TESTS:
    got = detect_crisis(phrase)
    mark = "OK " if got == expected else "FAIL"
    if got != expected:
        fails += 1
    print(f"[{mark}] {phrase!r} -> {got} (attendu {expected})")

print("---")
print(f"{len(TESTS) - fails}/{len(TESTS)} corrects")
sys.exit(1 if fails else 0)
