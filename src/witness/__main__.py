"""CLI: build a Long Witness ledger from a decision log + Aruba trace.

Usage:
    python -m witness build --decisions decision_log.jsonl \
        --trace aruba.txt --out ledger.jsonl
Prints a JSON summary (records, build seconds, bytes) to stdout.
"""

import argparse
import hashlib
import json
import time

from .ledger import build_ledger
from .trace import Trace


def main():
    ap = argparse.ArgumentParser(prog="witness")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--decisions", required=True)
    b.add_argument("--trace", required=True)
    b.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.trace, "rb") as fh:
        trace_md5 = hashlib.md5(fh.read()).hexdigest()
    decisions = [json.loads(line) for line in open(args.decisions)
                 if line.strip()]
    t0 = time.perf_counter()
    trace = Trace(args.trace)
    lines = build_ledger(
        trace, decisions,
        source_note="HouseRules decision_log.jsonl + CASAS Aruba trace "
                    "(Zenodo 17180309, CC BY 4.0)",
        trace_md5=trace_md5)
    build_seconds = time.perf_counter() - t0
    text = "\n".join(lines) + "\n"
    with open(args.out, "w") as fh:
        fh.write(text)
    print(json.dumps({
        "records": len(decisions),
        "build_seconds": round(build_seconds, 3),
        "ledger_bytes": len(text.encode("utf-8")),
        "trace_events": len(trace.times),
        "zones": trace.zones,
    }, indent=1))


if __name__ == "__main__":
    main()
