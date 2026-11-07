"""Golden test: the tool must reproduce the expected answers exactly (no missing, no extra rows).

Uses tests/fixtures/validation/ (the real Validation Set, once released) if it
contains expected_findings.csv, otherwise the synthetic look-alikes.
"""
import csv
from pathlib import Path

import pytest

from netcheck.core.analysis import analyze_folder, write_results

FIX = Path(__file__).parent / "fixtures"
SETS = [d for d in (FIX / "validation", FIX / "synthetic") if (d / "expected_findings.csv").exists()]


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [tuple(r) for r in csv.reader(fh)][1:]


@pytest.mark.parametrize("folder", SETS, ids=lambda p: p.name)
def test_reproduces_expected_answers(folder, tmp_path):
    results = analyze_folder(folder)
    f_csv, s_csv = write_results(results, tmp_path)
    got_f, exp_f = set(_rows(f_csv)), set(_rows(folder / "expected_findings.csv"))
    assert not (exp_f - got_f), f"missing rows: {sorted(exp_f - got_f)}"
    assert not (got_f - exp_f), f"extra rows: {sorted(got_f - exp_f)}"
    assert dict(_rows(s_csv)) == dict(_rows(folder / "expected_scores.csv"))


@pytest.mark.parametrize("folder", SETS, ids=lambda p: p.name)
def test_deterministic(folder, tmp_path):
    a = write_results(analyze_folder(folder), tmp_path / "a")
    b = write_results(analyze_folder(folder), tmp_path / "b")
    assert a[0].read_bytes() == b[0].read_bytes()
    assert a[1].read_bytes() == b[1].read_bytes()


def test_before_after_shows_three_resolved():
    from netcheck.core.analysis import analyze_file
    from netcheck.core.diff import compare
    d = FIX / "synthetic"
    diff = compare(analyze_file(d / "V6a_before.xml"), analyze_file(d / "V6b_after.xml"))
    assert len(diff["resolved_findings"]) == 3
    assert diff["score_before"] == 60 and diff["score_after"] == 100
