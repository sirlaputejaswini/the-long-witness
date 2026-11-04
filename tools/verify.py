#!/usr/bin/env python3
"""Long Witness full verifier — INDEPENDENT implementation.

Written from SPEC.md only. Imports nothing from the witness package.
Given a ledger and the sensor trace named in its header, it re-checks
the hash chain, the trailer, and every consequence anchor (SPEC §8).

Usage: python3 tools/verify.py LEDGER TRACE
Prints one JSON verdict line to stdout:
  {"ok": true, "records": N, "seconds": S}
  {"ok": false, "records": N, "first_failure_seq": k, "check": "..."}
"""

import hashlib
import json
import sys
import time
from bisect import bisect_left
from datetime import datetime, timezone


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def ts_epoch(text):
    fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in text else "%Y-%m-%d %H:%M:%S"
    return datetime.strptime(text, fmt).replace(
        tzinfo=timezone.utc).timestamp()


def load_trace(path):
    times, lines, sensors = [], [], []
    with open(path) as fh:
        for raw in fh:
            p = raw.split()
            if len(p) < 4:
                continue
            times.append(ts_epoch(p[0] + " " + p[1]))
            lines.append(p[0] + " " + p[1] + " " + p[2] + " " + p[3])
            sensors.append(p[2])
    return times, lines, sensors


def main():
    ledger_path, trace_path = sys.argv[1], sys.argv[2]
    started = time.perf_counter()
    raw_lines = [l for l in open(ledger_path).read().splitlines() if l.strip()]
    verdict = {"ok": False, "records": 0}

    def fail(seq, check):
        verdict.update(first_failure_seq=seq, check=check,
                       seconds=round(time.perf_counter() - started, 3))
        print(json.dumps(verdict))
        sys.exit(0)

    header = json.loads(raw_lines[0])
    if header.get("format") != "long-witness" or header.get("version") != 1:
        fail(0, "header")
    with open(trace_path, "rb") as fh:
        if hashlib.md5(fh.read()).hexdigest() != header.get("trace_md5"):
            fail(0, "trace_md5")
    window_seconds = header["anchor_window_seconds"]
    times, tlines, tsensors = load_trace(trace_path)

    trailer = json.loads(raw_lines[-1])
    records = [json.loads(l) for l in raw_lines[1:-1]]
    verdict["records"] = len(records)
    prev = header["genesis"]
    hashes = []
    for i, rec in enumerate(records, start=1):
        if rec.get("seq") != i:
            fail(i, "seq")
        if rec.get("prev") != prev:
            fail(i, "prev_link")
        body = {k: v for k, v in rec.items() if k != "hash"}
        digest = hashlib.sha256(
            (prev + "\n" + canon(body)).encode("utf-8")).hexdigest()
        if digest != rec.get("hash"):
            fail(i, "record_hash")
        # Anchor re-check from the trace (SPEC section 5).
        t0 = ts_epoch(rec["at"].replace("T", " "))
        lo = bisect_left(times, t0)
        hi = bisect_left(times, t0 + window_seconds)
        h = hashlib.sha256()
        for j in range(lo, hi):
            h.update((tlines[j] + "\n").encode("utf-8"))
        anchor = rec["anchor"]
        expect = {
            "event_count": hi - lo,
            "door_events": sum(1 for j in range(lo, hi)
                               if tsensors[j].startswith("D")),
            "sensors": sorted({tsensors[j] for j in range(lo, hi)}),
            "first_event": tlines[lo] if hi > lo else None,
            "last_event": tlines[hi - 1] if hi > lo else None,
            "digest": h.hexdigest(),
        }
        for key, want in expect.items():
            if anchor.get(key) != want:
                fail(i, "anchor_" + key)
        prev = rec["hash"]
        hashes.append(prev)
    if trailer.get("kind") != "trailer" or trailer.get("records") != len(records):
        fail(len(records), "trailer_count")
    if trailer.get("final_hash") != prev:
        fail(len(records), "trailer_final_hash")
    chain = hashlib.sha256("".join(hashes).encode("utf-8")).hexdigest()
    if trailer.get("chain_hash") != chain:
        fail(len(records), "trailer_chain_hash")
    verdict.update(ok=True, seconds=round(time.perf_counter() - started, 3))
    print(json.dumps(verdict))


if __name__ == "__main__":
    main()
