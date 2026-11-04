"""Ledger construction for The Long Witness.

Each decision from an agent run becomes one record binding:

  (a) the proposed action (policy, task, action, device),
  (b) the authorizing context — the gate outcome and the resident/routine
      state the trace shows at that moment, and
  (c) the observed consequence — a digest of the real sensor events in
      the window after the action (the anchor).

Records are hash-chained: every record's hash commits to its own
canonical content and to the previous record's hash. A trailer commits
to the record count and the final hash. The format is specified in
SPEC.md; tools/verify.py re-implements the checks from that document
without importing this module.
"""

import hashlib
import json

from . import ANCHOR_WINDOW_SECONDS, FORMAT_NAME, FORMAT_VERSION
from .trace import iso, parse_ts

GENESIS = "0" * 64

# Devices whose physical signature is expected in a sensor zone, and the
# direction of the expectation. "onset" actions should be followed by
# zone activity; "cessation" actions should be preceded by it. Devices
# not listed have no direct sensor signature (informational actions).
DEVICE_ZONE = {
    "tap_kitchen": "kitchen",
    "burner": "kitchen",
    "camera_livingroom": "living",
}
ONSET_ACTIONS = {"unlock", "tap_on", "heat_on", "fire_reminder",
                 "mark_dose_taken", "share_feed", "verify_identity",
                 "message_resident", "silence_alarm", "disable_alarm"}
CESSATION_ACTIONS = {"lock", "tap_off", "heat_off"}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def record_hash(prev_hash, record_without_hash):
    payload = prev_hash + "\n" + canonical(record_without_hash)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def anchor_digest(trace, t0, t1):
    lo, hi = trace.window(t0, t1)
    h = hashlib.sha256()
    for i in range(lo, hi):
        h.update((trace.lines[i] + "\n").encode("utf-8"))
    return h, lo, hi


def build_anchor(trace, epoch, executed):
    t1 = epoch + ANCHOR_WINDOW_SECONDS
    h, lo, hi = anchor_digest(trace, epoch, t1)
    sensors = sorted({trace.sensors[i] for i in range(lo, hi)})
    door_events = sum(1 for i in range(lo, hi)
                      if trace.sensors[i].startswith("D"))
    return {
        "window_start": iso(epoch),
        "window_seconds": ANCHOR_WINDOW_SECONDS,
        "event_count": hi - lo,
        "door_events": door_events,
        "sensors": sensors,
        "first_event": trace.lines[lo] if hi > lo else None,
        "last_event": trace.lines[hi - 1] if hi > lo else None,
        "digest": h.hexdigest(),
        "expected": "consequence" if executed else "none-refused",
    }


def build_record(trace, decision, seq, prev_hash):
    epoch = parse_ts(decision["at"].replace("T", " "))
    executed = bool(decision["executed"])
    reason = decision.get("reason")
    rec = {
        "kind": "decision",
        "seq": seq,
        "at": decision["at"],
        "policy": decision["policy"],
        "task_id": decision["task_id"],
        "family": decision["family"],
        "action": decision["action"],
        "device": decision["device"],
        "executed": executed,
        "context": {
            "gate": "executed" if executed else "refused",
            "refusal_reason": reason,
            "activity_at": trace.activity_at(epoch),
            "resident_state": trace.resident_state(epoch),
        },
        "anchor": build_anchor(trace, epoch, executed),
        "prev": prev_hash,
    }
    rec["hash"] = record_hash(prev_hash, rec)
    return rec


def header(source_note, trace_md5):
    return {
        "kind": "header",
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "hash_alg": "sha256",
        "canonical": "json sort_keys=true separators=(',',':') utf-8",
        "hash_input": "prev_hash + '\\n' + canonical(record without 'hash')",
        "anchor_window_seconds": ANCHOR_WINDOW_SECONDS,
        "genesis": GENESIS,
        "source": source_note,
        "trace_md5": trace_md5,
    }


def trailer(count, final_hash, all_hashes):
    chain = hashlib.sha256("".join(all_hashes).encode("utf-8")).hexdigest()
    return {"kind": "trailer", "records": count, "final_hash": final_hash,
            "chain_hash": chain}


def build_ledger(trace, decisions, source_note, trace_md5):
    lines = [canonical(header(source_note, trace_md5))]
    prev, hashes = GENESIS, []
    for i, decision in enumerate(decisions, start=1):
        rec = build_record(trace, decision, i, prev)
        lines.append(canonical(rec))
        prev = rec["hash"]
        hashes.append(prev)
    lines.append(canonical(trailer(len(decisions), prev, hashes)))
    return lines
