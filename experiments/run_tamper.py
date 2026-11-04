#!/usr/bin/env python3
"""Standalone tamper battery (E3) + longevity agreement (E4).

Writes each case result to results/e3_cases.jsonl as it completes
(flush + fsync per case), so a interrupted run loses nothing. On
completion, aggregates results/e3_tamper.json and
results/e4_longevity.json. Safe to re-run: completed case indices in
the JSONL are skipped.
"""

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "experiments"))
from run_experiments import tamper_variants, run_tool, TRACE, LEDGER  # noqa: E402
import random  # noqa: E402

CASES_LOG = os.path.join(ROOT, "results", "e3_cases.jsonl")


def main():
    lines = [l for l in open(LEDGER).read().splitlines() if l.strip()]
    cases = tamper_variants(lines, random.Random(20261103))
    done = {}
    if os.path.exists(CASES_LOG):
        for line in open(CASES_LOG):
            row = json.loads(line)
            done[row["case"]] = row
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "case.jsonl")
        for idx, (cls, mut) in enumerate(cases):
            if idx in done:
                continue
            with open(path, "w") as fh:
                fh.write("\n".join(mut) + "\n")
            full = run_tool("verify.py", path, TRACE)
            mini = run_tool("mini_reader.py", path)
            row = {"case": idx, "class": cls,
                   "detected": not full["ok"],
                   "failed_check": full.get("check"),
                   "mini_agrees": full["ok"] == mini["ok"]}
            with open(CASES_LOG, "a") as fh:
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            done[idx] = row
            print("case", idx, cls, row["detected"], flush=True)
    per_class = {}
    agreements = 0
    for row in done.values():
        slot = per_class.setdefault(row["class"],
                                    {"cases": 0, "detected": 0, "missed": 0})
        slot["cases"] += 1
        slot["detected" if row["detected"] else "missed"] += 1
        agreements += bool(row["mini_agrees"])
    for slot in per_class.values():
        slot["detection_rate"] = round(slot["detected"] / slot["cases"], 4)
    e3 = {"seed": 20261103, "total_cases": len(done), "per_class": per_class,
          "detail": [done[k] for k in sorted(done)]}
    json.dump(e3, open(os.path.join(ROOT, "results", "e3_tamper.json"), "w"),
              indent=1)
    clean_mini = run_tool("mini_reader.py", LEDGER)
    e4 = {"implementations": "tools/mini_reader.py written from SPEC.md only",
          "clean_ledger_mini_ok": clean_mini["ok"],
          "cases_compared": len(done), "agreements": agreements,
          "agreement_rate": round(agreements / len(done), 4)}
    json.dump(e4, open(os.path.join(ROOT, "results", "e4_longevity.json"), "w"),
              indent=1)
    print("E3", json.dumps(per_class), flush=True)
    print("E4", json.dumps(e4), flush=True)


if __name__ == "__main__":
    main()
