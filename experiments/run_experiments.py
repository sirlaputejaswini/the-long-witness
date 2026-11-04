#!/usr/bin/env python3
"""The Long Witness — experiments E1..E5.

Every number written to results/*.json comes from an actual run in this
script. E3/E4 run the standalone tools (tools/verify.py,
tools/mini_reader.py) as subprocesses, so the thing being measured is
the shipped artifact, not an in-process shortcut.

Usage: python3 experiments/run_experiments.py [--skip-tamper]
"""

import argparse
import bisect
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
HR = os.path.expanduser(
    "~/workspace/goals/conference-paper-publishing/files/house-rules")
DECISIONS = os.path.join(HR, "results", "decision_log.jsonl")
TRACE = os.path.join(HR, "data", "aruba.txt")
LEDGER = os.path.join(ROOT, "results", "ledger.jsonl")
RESULTS = os.path.join(ROOT, "results")
SEED = 20261103


def run_tool(script, *args):
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", script),
                          *args], capture_output=True, text=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------- E1 + E2
def e1_e2():
    from witness.ledger import build_ledger
    from witness.trace import Trace
    decisions = [json.loads(l) for l in open(DECISIONS) if l.strip()]
    trace_md5 = hashlib.md5(open(TRACE, "rb").read()).hexdigest()
    t0 = time.perf_counter()
    trace = Trace(TRACE)
    lines = build_ledger(trace, decisions, "HouseRules decision_log.jsonl "
                         "+ CASAS Aruba trace (Zenodo 17180309, CC BY 4.0)",
                         trace_md5)
    build_s = time.perf_counter() - t0
    text = "\n".join(lines) + "\n"
    with open(LEDGER, "w") as fh:
        fh.write(text)
    ledger_bytes = len(text.encode())
    source_bytes = os.path.getsize(DECISIONS)
    e1 = {"records": len(decisions), "build_seconds": round(build_s, 3),
          "ledger_bytes": ledger_bytes, "source_decision_log_bytes": source_bytes,
          "overhead_pct": round(100.0 * (ledger_bytes - source_bytes) / source_bytes, 2),
          "bytes_per_record": round(ledger_bytes / len(decisions), 1),
          "trace_events": len(trace.times)}
    json.dump(e1, open(os.path.join(RESULTS, "e1_build.json"), "w"), indent=1)

    t0 = time.perf_counter()
    verdict = run_tool("verify.py", LEDGER, TRACE)
    wall = time.perf_counter() - t0
    e2 = {"verdict": verdict, "wall_seconds": round(wall, 3),
          "verify_seconds_reported": verdict["seconds"],
          "per_10000_records_seconds": round(
              verdict["seconds"] / verdict["records"] * 10000, 3)}
    json.dump(e2, open(os.path.join(RESULTS, "e2_verify.json"), "w"), indent=1)
    return e1, e2


# ---------------------------------------------------------------- E3 + E4
def tamper_variants(lines, rng):
    """Yield (class_name, mutated_lines). lines = ledger lines (str)."""
    header, trailer = lines[0], lines[-1]
    records = lines[1:-1]
    n = len(records)
    cases = []

    def pick():
        return rng.randrange(n)

    for _ in range(20):  # alter an action
        i = pick()
        rec = json.loads(records[i])
        rec["action"] = "lock" if rec["action"] != "lock" else "unlock"
        mut = records[:]
        mut[i] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
        cases.append(("alter_action", [header] + mut + [trailer]))
    for _ in range(20):  # delete a record
        i = pick()
        mut = records[:i] + records[i + 1:]
        cases.append(("delete_record", [header] + mut + [trailer]))
    for _ in range(20):  # reorder two records
        i = pick()
        j = (i + rng.randrange(1, 50)) % n
        mut = records[:]
        mut[i], mut[j] = mut[j], mut[i]
        cases.append(("reorder_records", [header] + mut + [trailer]))
    for _ in range(20):  # alter a consequence anchor
        i = pick()
        rec = json.loads(records[i])
        rec["anchor"]["event_count"] += 1
        rec["anchor"]["digest"] = "f" * 64
        mut = records[:]
        mut[i] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
        cases.append(("alter_consequence", [header] + mut + [trailer]))
    for _ in range(20):  # forge an authorizing context
        i = pick()
        rec = json.loads(records[i])
        rec["context"]["resident_state"] = (
            "home" if rec["context"]["resident_state"] != "home" else "away")
        rec["context"]["gate"] = "executed"
        mut = records[:]
        mut[i] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
        cases.append(("forge_context", [header] + mut + [trailer]))
    for _ in range(5):   # truncate tail, trailer kept (count now wrong)
        k = rng.randrange(1, 20)
        cases.append(("truncate_tail_trailer_kept",
                      [header] + records[:-k] + [trailer]))
    for _ in range(5):   # truncate tail AND trailer (malformed ledger)
        k = rng.randrange(1, 20)
        cases.append(("truncate_tail_and_trailer",
                      [header] + records[:-k]))
    for _ in range(5):   # truncate tail, then REFORGE a consistent trailer
        k = rng.randrange(1, 20)
        kept = records[:-k]
        kept_hashes = [json.loads(r)["hash"] for r in kept]
        import hashlib as _hl
        forged = json.dumps(
            {"kind": "trailer", "records": len(kept),
             "final_hash": kept_hashes[-1],
             "chain_hash": _hl.sha256(
                 "".join(kept_hashes).encode("utf-8")).hexdigest()},
            sort_keys=True, separators=(",", ":"))
        cases.append(("truncate_and_reforge_trailer",
                      [header] + kept + [forged]))
    return cases


def e3_e4():
    lines = [l for l in open(LEDGER).read().splitlines() if l.strip()]
    rng = random.Random(SEED)
    cases = tamper_variants(lines, rng)
    per_class = {}
    agreements, total = 0, 0
    detail = []
    with tempfile.TemporaryDirectory() as td:
        for idx, (cls, mut) in enumerate(cases):
            path = os.path.join(td, "case.jsonl")
            with open(path, "w") as fh:
                fh.write("\n".join(mut) + "\n")
            full = run_tool("verify.py", path, TRACE)
            mini = run_tool("mini_reader.py", path)
            detected = not full["ok"]
            agree = (full["ok"] == mini["ok"])
            agreements += agree
            total += 1
            slot = per_class.setdefault(
                cls, {"cases": 0, "detected": 0, "missed": 0})
            slot["cases"] += 1
            slot["detected" if detected else "missed"] += 1
            detail.append({"case": idx, "class": cls, "detected": detected,
                           "failed_check": full.get("check"),
                           "mini_agrees": agree})
    for slot in per_class.values():
        slot["detection_rate"] = round(slot["detected"] / slot["cases"], 4)
    e3 = {"seed": SEED, "total_cases": total, "per_class": per_class,
          "detail": detail}
    json.dump(e3, open(os.path.join(RESULTS, "e3_tamper.json"), "w"), indent=1)
    clean_mini = run_tool("mini_reader.py", LEDGER)
    e4 = {"implementations": "tools/mini_reader.py written from SPEC.md only",
          "clean_ledger_mini_ok": clean_mini["ok"],
          "cases_compared": total, "agreements": agreements,
          "agreement_rate": round(agreements / total, 4)}
    json.dump(e4, open(os.path.join(RESULTS, "e4_longevity.json"), "w"), indent=1)
    return e3, e4


# ---------------------------------------------------------------- E5
def e5():
    """Consequence check with its own trace parse (no builder code):
    for each executed decision, does the sensor record show the physical
    signature the action claims? Zones derived here from activity labels
    exactly as documented in SPEC/DATA_NOTES (top-8 motion sensors per
    label). Informational actions have no sensor signature and are
    counted separately, never scored."""
    times, sensors = [], []
    intervals, open_lbl = [], {}
    for raw in open(TRACE):
        p = raw.split()
        if len(p) < 4:
            continue
        stamp = p[0] + " " + p[1]
        dt = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S.%f" if "." in stamp
                               else "%Y-%m-%d %H:%M:%S")
        times.append(dt.replace(tzinfo=timezone.utc).timestamp())
        sensors.append(p[2])
        if len(p) >= 6 and p[-1] in ("begin", "end"):
            if p[-1] == "begin":
                open_lbl[p[-2]] = times[-1]
            elif p[-2] in open_lbl:
                intervals.append((open_lbl.pop(p[-2]), times[-1], p[-2]))
    counts = {"Meal_Preparation": Counter(), "Relax": Counter()}
    for s, e, lbl in intervals:
        if lbl in counts:
            for i in range(bisect.bisect_left(times, s),
                           bisect.bisect_right(times, e)):
                if sensors[i].startswith("M"):
                    counts[lbl][sensors[i]] += 1
    kitchen = {s for s, _ in counts["Meal_Preparation"].most_common(8)}
    living = {s for s, _ in counts["Relax"].most_common(8)}

    def window_sensors(t0, t1):
        lo = bisect.bisect_left(times, t0)
        hi = bisect.bisect_left(times, t1)
        return [sensors[i] for i in range(lo, hi)]

    groups = {}
    absence = {}
    no_signature = 0
    recs = [json.loads(l) for l in open(LEDGER).read().splitlines()[1:-1]]
    for rec in recs:
        if not rec["executed"]:
            continue
        dev, act = rec["device"], rec["action"]
        t0 = datetime.strptime(rec["at"].replace("T", " "),
                               "%Y-%m-%d %H:%M:%S.%f" if "." in rec["at"]
                               else "%Y-%m-%d %H:%M:%S")
        t0 = t0.replace(tzinfo=timezone.utc).timestamp()
        if dev == "front_door":
            name = "front_door (any door-sensor event, following 10 min)"
            got = window_sensors(t0, t0 + 600)
            hit = any(s.startswith("D") for s in got)
            slot = groups.setdefault(name, {"checked": 0, "matched": 0,
                                            "matched_preceding": 0,
                                            "matched_symmetric": 0})
            slot["checked"] += 1
            slot["matched"] += bool(hit)
            before = window_sensors(t0 - 600, t0)
            hit_b = any(s.startswith("D") for s in before)
            slot["matched_preceding"] += bool(hit_b)
            slot["matched_symmetric"] += bool(hit or hit_b)
            continue
        elif dev in ("tap_kitchen", "burner"):
            zone = kitchen
            if act in ("tap_off", "heat_off"):
                name = dev + " cessation (kitchen motion, preceding 10 min)"
                got = window_sensors(t0 - 600, t0)
            else:
                name = dev + " onset (kitchen motion, following 10 min)"
                got = window_sensors(t0, t0 + 600)
            hit = any(s in zone for s in got)
        elif dev == "med_reminder":
            name = "med_reminder (any sensor event, following 10 min)"
            got = window_sensors(t0, t0 + 600)
            hit = len(got) > 0
        elif dev == "camera_livingroom":
            # A shared feed leaves no motion of its own. The observable
            # signature is of the ABSENCE type: the executed shares in
            # this run happened while the resident was away, so the
            # honest check is whether the window shows the empty house
            # the context claims. Scored separately, never merged into
            # the positive-signature rate.
            got = window_sensors(t0, t0 + 600)
            empty = not any(s in living for s in got)
            slot = absence.setdefault(
                "camera_livingroom (no living-zone motion, following "
                "10 min)", {"checked": 0, "window_empty_of_living_motion": 0,
                            "resident_away": 0})
            slot["checked"] += 1
            slot["window_empty_of_living_motion"] += bool(empty)
            slot["resident_away"] += bool(
                rec["context"]["resident_state"] == "away")
            continue
        else:  # smoke_alarm: silencing/disabling leaves no CASAS signature
            no_signature += 1
            continue
        slot = groups.setdefault(name, {"checked": 0, "matched": 0})
        slot["checked"] += 1
        slot["matched"] += bool(hit)
    tot_c = sum(g["checked"] for g in groups.values())
    tot_m = sum(g["matched"] for g in groups.values())
    for g in groups.values():
        g["match_rate"] = round(g["matched"] / g["checked"], 4)
        if "matched_preceding" in g:
            g["match_rate_preceding"] = round(
                g["matched_preceding"] / g["checked"], 4)
            g["match_rate_symmetric"] = round(
                g["matched_symmetric"] / g["checked"], 4)
    out = {"executed_records": sum(1 for r in recs if r["executed"]),
           "scored": tot_c, "matched": tot_m,
           "overall_match_rate": round(tot_m / tot_c, 4),
           "no_sensor_signature_excluded": no_signature,
           "absence_signature_groups": absence,
           "groups": groups,
           "kitchen_zone": sorted(kitchen), "living_zone": sorted(living)}
    json.dump(out, open(os.path.join(RESULTS, "e5_consequence.json"), "w"),
              indent=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-tamper", action="store_true")
    args = ap.parse_args()
    e1, e2 = e1_e2()
    print("E1", json.dumps(e1))
    print("E2", json.dumps(e2))
    if not args.skip_tamper:
        e3, e4 = e3_e4()
        print("E3", json.dumps(e3["per_class"]))
        print("E4", json.dumps(e4))
    e5r = e5()
    print("E5", json.dumps(e5r))


if __name__ == "__main__":
    main()
