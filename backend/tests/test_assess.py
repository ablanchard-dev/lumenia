"""Tests des scores cliniques (app.assess) : PHQ-9, GAD-7, entrée."""
import pytest

from app.assess import entry_score, gad7_score, phq9_score


def nine(total):
    """9 items dont le total vaut `total` et item9 = 0."""
    return [total, 0, 0, 0, 0, 0, 0, 0, 0]


@pytest.mark.parametrize("total,severity", [
    (0, "minimal"),
    (4, "minimal"),
    (5, "mild"),
    (9, "mild"),
    (10, "moderate"),
    (14, "moderate"),
    (15, "moderately severe"),
    (19, "moderately severe"),
    (20, "severe"),
    (27, "severe"),
])
def test_phq9_severity_thresholds(total, severity):
    t, sev, _ = phq9_score(nine(total))
    assert t == total
    assert sev == severity


def test_phq9_sums_only_first_nine():
    t, _, _ = phq9_score([1, 1, 1, 1, 1, 1, 1, 1, 1, 99])
    assert t == 9


def test_phq9_risk_from_item9_in_list():
    _, _, risk = phq9_score([0, 0, 0, 0, 0, 0, 0, 0, 2])
    assert risk is True


def test_phq9_no_risk_when_item9_zero():
    _, _, risk = phq9_score(nine(12))
    assert risk is False


def test_phq9_explicit_item9_overrides_list():
    # item9 du paramètre prime sur items[8]
    _, _, risk = phq9_score([0, 0, 0, 0, 0, 0, 0, 0, 3], item9=0)
    assert risk is False
    _, _, risk2 = phq9_score(nine(2), item9=1)
    assert risk2 is True


@pytest.mark.parametrize("total,severity", [
    (0, "minimal"),
    (4, "minimal"),
    (5, "mild"),
    (9, "mild"),
    (10, "moderate"),
    (14, "moderate"),
    (15, "severe"),
    (21, "severe"),
])
def test_gad7_severity_thresholds(total, severity):
    t, sev = gad7_score([total, 0, 0, 0, 0, 0, 0])
    assert t == total
    assert sev == severity


def test_gad7_sums_only_first_seven():
    t, _ = gad7_score([1, 1, 1, 1, 1, 1, 1, 100])
    assert t == 7


def test_entry_score_returns_copy():
    src = {"laterale": 2, "logique": 1}
    out = entry_score(src)
    assert out == src
    out["laterale"] = 99
    assert src["laterale"] == 2  # l'original n'est pas muté
