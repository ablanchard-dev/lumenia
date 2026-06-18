# -*- coding: utf-8 -*-
"""Construit la banque d'entrée unifiée `app/entry_bank.json`.

Fusionne deux sources :
  - `_bank_source_200.csv` : 200 items cognitifs originaux (5 domaines type WAIS,
    120 QCM + 80 réponse libre stricte) ;
  - `_bank_legacy.json`    : la banque écrite à la main (latérale, logique,
    arithmétique, similitudes, expression libre).

Six dimensions canoniques en sortie : verbale, fluide, memoire, spatial, vitesse
(notées) + libre (expression libre, non notée — alimente le profilage §3.3).
Le `kind` est porté par CHAQUE item (qcm / objective / open), plus par dimension.

Idempotent : régénère le JSON depuis les deux sources. Lancement depuis backend/ :
    .venv\\Scripts\\python.exe _build_bank.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
CSV_SRC = HERE / "_bank_source_200.csv"
LEGACY = HERE / "_bank_legacy.json"
OUT = HERE / "app" / "entry_bank.json"

# Domaine du CSV -> dimension canonique.
DOMAIN_TO_DIM = {
    "Compréhension verbale": "verbale",
    "Raisonnement fluide": "fluide",
    "Mémoire de travail": "memoire",
    "Raisonnement visuo-spatial": "spatial",
    "Vitesse de traitement / attention": "vitesse",
}
# Ancienne dimension -> dimension canonique (fusion intelligente).
LEGACY_TO_DIM = {
    "laterale": "verbale",
    "similitudes": "verbale",
    "logique": "fluide",
    "arithmetique": "fluide",
    "creative": "libre",
}
DIM_ORDER = ["verbale", "fluide", "memoire", "spatial", "vitesse", "libre"]
DIM_LABEL = {
    "verbale": "Compréhension verbale",
    "fluide": "Raisonnement fluide",
    "memoire": "Mémoire de travail",
    "spatial": "Raisonnement visuo-spatial",
    "vitesse": "Vitesse & attention",
    "libre": "Expression libre",
}


def _int(value, default):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def from_csv() -> dict[str, list]:
    items: dict[str, list] = {d: [] for d in DIM_ORDER}
    with CSV_SRC.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dim = DOMAIN_TO_DIM[row["domaine"].strip()]
            item = {
                "id": row["id"].strip(),
                "domaine": row["domaine"].strip(),
                "sous_type": row["sous_type"].strip(),
                "niveau": _int(row["niveau_1_5"], 2),
                "temps_sec": _int(row["temps_conseille_sec"], 45),
                "consigne": row["consigne_examinateur"].strip(),
                "question": row["stimulus"].strip(),
            }
            if row["mode_reponse"].strip().upper() == "QCM":
                item["kind"] = "qcm"
                item["choices"] = {
                    "A": row["choix_A"].strip(),
                    "B": row["choix_B"].strip(),
                    "C": row["choix_C"].strip(),
                    "D": row["choix_D"].strip(),
                }
                item["answer"] = row["reponse_attendue"].strip().upper()
                item["explication"] = row["explication_correction"].strip()
            else:  # réponse libre stricte -> type "objective" existant
                item["kind"] = "objective"
                item["answers"] = [row["reponse_attendue"].strip()]
                item["hint"] = row["explication_correction"].strip()
            items[dim].append(item)
    return items


def from_legacy() -> dict[str, list]:
    items: dict[str, list] = {d: [] for d in DIM_ORDER}
    legacy = json.loads(LEGACY.read_text(encoding="utf-8"))
    for step in legacy:
        dim = LEGACY_TO_DIM[step["dimension"]]
        kind = step["kind"]  # ancien kind au niveau dimension
        for it in step["pool"]:
            new = {"id": it["id"], "kind": kind, "question": it["question"]}
            if kind == "objective":
                new["answers"] = it["answers"]
                new["hint"] = it.get("hint", "")
            items[dim].append(new)
    return items


def main() -> None:
    csv_items = from_csv()
    legacy_items = from_legacy()
    bank, seen = [], set()
    for dim in DIM_ORDER:
        pool = []
        for it in csv_items[dim] + legacy_items[dim]:
            if it["id"] in seen:  # garde-fou collision d'ids entre sources
                it = {**it, "id": f"{it['id']}_x"}
            seen.add(it["id"])
            pool.append(it)
        bank.append({"dimension": dim, "label": DIM_LABEL[dim], "pool": pool})

    OUT.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(len(s["pool"]) for s in bank)
    print(f"OK : {total} items, {len(bank)} dimensions -> {OUT.relative_to(HERE)}")
    for s in bank:
        kinds: dict[str, int] = {}
        for it in s["pool"]:
            kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
        print(f"  {s['dimension']:8} {len(s['pool']):3}  {kinds}")


if __name__ == "__main__":
    main()
