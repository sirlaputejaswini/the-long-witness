"""Small-chain tests: build 3 records from synthetic decisions against a
tiny in-memory trace stand-in, then check the chain invariants."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from witness.ledger import GENESIS, build_ledger, canonical, record_hash  # noqa: E402
import json  # noqa: E402


class FakeTrace:
    times = [1000.0, 1060.0]
    lines = ["2010-01-01 00:16:40.000000 M001 ON",
             "2010-01-01 00:17:40.000000 D001 OPEN"]
    sensors = ["M001", "D001"]

    def activity_at(self, epoch):
        return "Sleeping"

    def resident_state(self, epoch):
        return "asleep"

    def window(self, t0, t1):
        idx = [i for i, t in enumerate(self.times) if t0 <= t < t1]
        return (idx[0], idx[-1] + 1) if idx else (0, 0)


DECISIONS = [
    {"policy": "p", "date": "2010-01-01", "task_id": "t1", "family": "f",
     "action": "unlock", "device": "front_door",
     "at": "2010-01-01T00:00:00", "executed": True, "reason": None},
    {"policy": "p", "date": "2010-01-01", "task_id": "t2", "family": "f",
     "action": "share_feed", "device": "camera_livingroom",
     "at": "2010-01-01T00:30:00", "executed": False, "reason": "privacy"},
]


def test_chain_links_and_hashes():
    lines = build_ledger(FakeTrace(), DECISIONS, "test", "0" * 32)
    assert json.loads(lines[0])["kind"] == "header"
    recs = [json.loads(l) for l in lines[1:-1]]
    assert recs[0]["prev"] == GENESIS
    assert recs[1]["prev"] == recs[0]["hash"]
    for rec in recs:
        body = {k: v for k, v in rec.items() if k != "hash"}
        assert record_hash(rec["prev"], body) == rec["hash"]
    trailer = json.loads(lines[-1])
    assert trailer["records"] == 2
    assert trailer["final_hash"] == recs[-1]["hash"]
    # Tampering with one field breaks that record's hash.
    recs[0]["action"] = "lock"
    body = {k: v for k, v in recs[0].items() if k != "hash"}
    assert record_hash(recs[0]["prev"], body) != recs[0]["hash"]
    assert canonical({"b": 1, "a": 2}) == '{"a":2,"b":1}'
