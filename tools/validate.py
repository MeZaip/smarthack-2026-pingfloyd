"""Check our output against a validation set's answer key (expected_findings.csv + expected_scores.csv).

Runs the real CLI end-to-end (`python -m netcheck analyze <folder> --out <tmp>`), exactly as
the graders will, then compares the produced CSVs row by row and prints a per-file report.

    .venv/bin/python tools/validate.py                        # defaults to public_validation_set/
    .venv/bin/python tools/validate.py tests/fixtures/synthetic public_validation_set
    .venv/bin/python tools/validate.py --keep out/            # keep the generated CSVs

Exit code 0 = everything matches, 1 = at least one problem, 2 = bad usage / missing answer key.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINDINGS_HEADER = ["file", "ip", "port", "finding_code", "severity"]
SCORES_HEADER = ["file", "network_score"]

USE_COLOR = sys.stdout.isatty()


def c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


OK, BAD, WARN = (lambda t: c(t, "32")), (lambda t: c(t, "31")), (lambda t: c(t, "33"))


def read_csv(path: Path) -> tuple[list[str], list[tuple[str, ...]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = [tuple(cell.strip() for cell in r) for r in csv.reader(fh) if any(x.strip() for x in r)]
    if not rows:
        return [], []
    return list(rows[0]), rows[1:]


def run_cli(folder: Path, out: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "netcheck", "analyze", str(folder), "--out", str(out)],
        cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def validate(folder: Path, keep: Path | None) -> int:
    """Return the number of problems found in this folder."""
    print(c(f"\n=== {folder} ===", "1"))
    exp_f_path, exp_s_path = folder / "expected_findings.csv", folder / "expected_scores.csv"
    if not exp_f_path.exists() or not exp_s_path.exists():
        print(BAD(f"  missing answer key (expected_findings.csv / expected_scores.csv) in {folder}"))
        return 1

    out = keep / folder.name if keep else Path(tempfile.mkdtemp(prefix="netcheck-validate-"))
    ok, log = run_cli(folder, out)
    if not ok:
        print(BAD("  CLI `netcheck analyze` failed:"))
        print("    " + log.replace("\n", "\n    "))
        return 1

    problems: list[str] = []

    got_fh, got_f = read_csv(out / "findings.csv")
    got_sh, got_s = read_csv(out / "scores.csv")
    if got_fh != FINDINGS_HEADER:
        problems.append(f"findings.csv header is {got_fh}, expected {FINDINGS_HEADER}")
    if got_sh != SCORES_HEADER:
        problems.append(f"scores.csv header is {got_sh}, expected {SCORES_HEADER}")

    _, exp_f = read_csv(exp_f_path)
    _, exp_s = read_csv(exp_s_path)

    # duplicates count as errors too ("no extra rows")
    for label, rows in (("findings.csv", got_f), ("scores.csv", got_s)):
        seen = set()
        for r in rows:
            if r in seen:
                problems.append(f"duplicate row in our {label}: {','.join(r)}")
            seen.add(r)

    exp_scores, got_scores = dict(exp_s), dict(got_s)
    xml_files = sorted(p.name for p in folder.iterdir() if p.suffix.lower() == ".xml")
    all_files = sorted(set(xml_files) | set(exp_scores) | set(got_scores)
                       | {r[0] for r in exp_f} | {r[0] for r in got_f})

    exp_by_file, got_by_file = defaultdict(set), defaultdict(set)
    for r in exp_f:
        exp_by_file[r[0]].add(r[1:])
    for r in got_f:
        got_by_file[r[0]].add(r[1:])

    total_rows = matched_rows = 0
    for name in all_files:
        file_problems, notes = [], []
        if name not in xml_files:
            file_problems.append("listed in the answer key / our output but no such .xml in the folder")
        if name not in exp_scores:
            notes.append(WARN("no expected score in the answer key (not graded?)"))
        exp_score, got_score = exp_scores.get(name), got_scores.get(name)
        if name in exp_scores and got_score is None:
            file_problems.append(f"score missing from our scores.csv (expected {exp_score})")
        elif name in exp_scores and got_score != exp_score:
            file_problems.append(f"score {got_score} != expected {exp_score}")

        exp_rows, got_rows = exp_by_file[name], got_by_file[name]
        total_rows += len(exp_rows)
        matched_rows += len(exp_rows & got_rows)
        for r in sorted(exp_rows - got_rows):
            file_problems.append(f"MISSING finding  ip={r[0]} port={r[1] or '-'} {r[2]} ({r[3]})")
        for r in sorted(got_rows - exp_rows):
            file_problems.append(f"EXTRA finding    ip={r[0]} port={r[1] or '-'} {r[2]} ({r[3]})")
        # hint: same ip/port/code but wrong severity
        exp_keys = {r[:3]: r[3] for r in exp_rows - got_rows}
        for r in got_rows - exp_rows:
            if r[:3] in exp_keys:
                notes.append(WARN(f"hint: {r[2]} on {r[0]}:{r[1] or '-'} has severity "
                                          f"{r[3]}, expected {exp_keys[r[:3]]}"))

        status = BAD("FAIL") if file_problems else OK("PASS")
        detail = f"score={got_score} findings={len(got_rows)}/{len(exp_rows)}"
        print(f"  [{status}] {name:<32} {detail}")
        for p in file_problems + notes:
            print(f"         - {p}")
        problems.extend(f"{name}: {p}" for p in file_problems)

    # determinism: a second run must produce byte-identical CSVs
    out2 = Path(tempfile.mkdtemp(prefix="netcheck-validate-"))
    ok2, _ = run_cli(folder, out2)
    for fname in ("findings.csv", "scores.csv"):
        if not ok2 or (out / fname).read_bytes() != (out2 / fname).read_bytes():
            problems.append(f"non-deterministic output: {fname} differs between two runs")

    for p in problems[:]:
        if p.startswith(("findings.csv header", "scores.csv header", "duplicate", "non-deterministic")):
            print(BAD(f"  ! {p}"))

    summary = (f"  {matched_rows}/{total_rows} expected findings matched, "
               f"{sum(1 for n in exp_scores if got_scores.get(n) == exp_scores[n])}/{len(exp_scores)} scores matched")
    print(summary)
    if keep:
        print(f"  outputs kept in {out}")
    return len(problems)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="*", type=Path, default=[ROOT / "public_validation_set"],
                    help="folders containing *.xml + expected_findings.csv + expected_scores.csv")
    ap.add_argument("--keep", type=Path, help="write our CSVs here (one subfolder per set) instead of a temp dir")
    args = ap.parse_args()

    total = 0
    for folder in args.folders:
        if not folder.is_dir():
            print(BAD(f"not a folder: {folder}"))
            return 2
        total += validate(folder.resolve(), args.keep.resolve() if args.keep else None)

    print()
    if total:
        print(BAD(f"FAILED: {total} problem(s) found"))
        return 1
    print(OK("ALL GOOD: output matches the answer key exactly"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
