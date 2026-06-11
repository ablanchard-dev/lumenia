from typing import Dict, List, Tuple

def entry_score(answers: Dict[str, int]) -> Dict[str, int]:
    return dict(answers)

def phq9_score(items: List[int], item9: int | None = None) -> Tuple[int, str, bool]:
    total = sum(items[:9])
    severity = (
        "minimal" if total <= 4 else
        "mild" if total <= 9 else
        "moderate" if total <= 14 else
        "moderately severe" if total <= 19 else
        "severe"
    )
    i9 = item9 if item9 is not None else (items[8] if len(items) >= 9 else 0)
    risk = i9 > 0
    return total, severity, risk

def gad7_score(items: List[int]) -> Tuple[int, str]:
    total = sum(items[:7])
    severity = (
        "minimal" if total <= 4 else
        "mild" if total <= 9 else
        "moderate" if total <= 14 else
        "severe"
    )
    return total, severity
