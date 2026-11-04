# The Long Witness — ledger format specification, version 1

This document specifies the `long-witness` ledger format completely
enough that an implementer with no access to the original software can
read a ledger, verify it, and write a compatible one. That is the point
of the format: the record must outlive the system that produced it.

## 1. File structure

A ledger is a UTF-8 text file of JSON Lines:

1. Exactly one **header** line.
2. Zero or more **decision record** lines, in chain order.
3. Exactly one **trailer** line, last.

## 2. Canonical form

All hashing uses the canonical form of a JSON object: keys sorted
lexicographically, separators `,` and `:` with no spaces, non-ASCII
characters unescaped, encoded as UTF-8. This is Python's
`json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
and any equivalent serializer in another language.

## 3. Header

```json
{"kind":"header","format":"long-witness","version":1,
 "hash_alg":"sha256","genesis":"<64 zero characters>",
 "anchor_window_seconds":600, "source":"<provenance note>",
 "trace_md5":"<md5 of the sensor trace the anchors were built from>"}
```

`genesis` is the string of 64 `0` characters. It is the `prev` value of
the first record.

## 4. Decision records

Each record is a JSON object with these fields:

| field | meaning |
|---|---|
| `kind` | always `"decision"` |
| `seq` | 1-based position in the chain, consecutive |
| `at` | ISO-8601 timestamp of the decision, as recorded by the agent run |
| `policy`, `task_id`, `family` | which agent, which task, which task family |
| `action`, `device` | the proposed action and the device it targets |
| `executed` | whether the gate let the action through |
| `context.gate` | `"executed"` or `"refused"` |
| `context.refusal_reason` | the gate's reason string, or `null` |
| `context.activity_at` | the activity label the home's recording shows at `at`, or `null` |
| `context.resident_state` | `"home"`, `"away"`, or `"asleep"`, derived from the recording (§6) |
| `anchor` | the consequence anchor (§5) |
| `prev` | the `hash` of the previous record, or `genesis` for `seq` 1 |
| `hash` | this record's chain hash (§4.1) |

### 4.1 Chain hash

```
hash = sha256_hex( prev + "\n" + canonical(record without the "hash" field) )
```

## 5. Consequence anchor

The anchor binds the record to what the home's sensors actually did
after the decision. For a decision at time `t`:

- The window is `[t, t + anchor_window_seconds)`.
- The event lines are the trace lines whose timestamps fall in the
  window, in trace order. A canonical event line is
  `"<YYYY-MM-DD> <HH:MM:SS.ffffff> <sensor> <value>"` — the first four
  whitespace-separated fields of a trace line.
- `digest` is the SHA-256 hex of the concatenation of each event line
  followed by `"\n"`, UTF-8. An empty window hashes the empty string.
- `event_count` is the number of event lines; `door_events` counts those
  whose sensor id starts with `D`; `sensors` is the sorted list of
  distinct sensor ids; `first_event` / `last_event` are the first and
  last canonical event lines, or `null` when the window is empty.
- `expected` is `"consequence"` when the action was executed and
  `"none-refused"` when the gate refused it (no consequence is claimed
  for a refused action; the window is still recorded as context).

## 6. Context derivation

From the trace's activity labels (intervals between `begin` and `end`
annotations): `activity_at` is the label whose interval contains `t`,
else `null`. `resident_state` is `"asleep"` if `activity_at` is
`"Sleeping"`; else `"away"` if `t` falls between a `Leave_Home` begin
and the next `Enter_Home` begin; else `"home"`.

Context fields are integrity-protected by the chain hash. A verifier
that holds the trace MAY re-derive them, but this specification does
not require it (see §8, limitations).

## 7. Trailer

```json
{"kind":"trailer","records":N,"final_hash":"<hash of record N>",
 "chain_hash":"<sha256 hex of the concatenation of all record hashes>"}
```

## 8. Verification

A **full verifier**, given a ledger and the trace named in the header:

1. Parses every line as JSON; checks the header's `format` and
   `version`, and the trace MD5 against the supplied trace.
2. For each record, in order: checks `seq`, checks `prev` equals the
   previous record's `hash` (or genesis), recomputes the chain hash
   and compares.
3. Recomputes every anchor from the trace (§5) and compares all anchor
   fields.
4. Checks the trailer: record count, final hash, chain hash.
5. Reports `ok` only if every check passes, else the `seq` of the
   first failing record and the failed check.

A **minimal reader** performs steps 1 (header only), 2, and 4: chain
integrity without the trace. It cannot detect a forged *trace*, and a
full verifier cannot detect tampering that rewrites the whole chain
*and* the trailer consistently while also matching a forged trace —
the ledger proves internal consistency and fidelity to one named
trace, not the trace's own truth. Anchoring to a trace whose MD5 is
published elsewhere is what ties the ledger to the world.
