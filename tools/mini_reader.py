#!/usr/bin/env python3
"""Long Witness MINIMAL reader — longevity-drill implementation.

Written only from SPEC.md (sections 1-4, 7, 8 "minimal reader"), as if
by a future implementer who has the spec and a ledger but none of the
original software and no sensor trace. Checks chain integrity only.

Usage: python3 tools/mini_reader.py LEDGER
Prints: {"ok": true|false, "records": N}
"""

import hashlib
import json
import sys


def main():
    lines = [l for l in open(sys.argv[1]).read().splitlines() if l.strip()]
    header = json.loads(lines[0])
    assert header["format"] == "long-witness" and header["version"] == 1
    prev = header["genesis"]
    hashes, count = [], 0
    ok = True
    for line in lines[1:-1]:
        rec = json.loads(line)
        count += 1
        if rec["seq"] != count or rec["prev"] != prev:
            ok = False
            break
        body = {k: v for k, v in rec.items() if k != "hash"}
        payload = prev + "\n" + json.dumps(
            body, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False)
        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != rec["hash"]:
            ok = False
            break
        prev = rec["hash"]
        hashes.append(prev)
    if ok:
        trailer = json.loads(lines[-1])
        chain = hashlib.sha256("".join(hashes).encode("utf-8")).hexdigest()
        ok = (trailer.get("records") == count
              and trailer.get("final_hash") == prev
              and trailer.get("chain_hash") == chain)
    print(json.dumps({"ok": ok, "records": count}))


if __name__ == "__main__":
    main()
