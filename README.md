# The Long Witness

**A witness layer for delegated action.** When an agent acts in the
physical world on someone's behalf, the record of that action usually
dies with the software that made it. The Long Witness keeps a different
kind of record: an append-only, hash-chained ledger in which every
entry binds three things that are normally kept apart —

1. **the action** the agent proposed,
2. **the authorizing context** — the gate outcome and the routine state
   that permitted it, and
3. **the observed consequence** — what the home's real sensors actually
   did next (*consequence anchoring*).

The format is plain text (JSON Lines), defined by a short written
specification ([SPEC.md](SPEC.md)), and verifiable by an implementation
that shares no code with the builder. The record is designed to
outlive the system that produced it — because three hundred years from
now, the foundational problem of delegated action will not be
capability. It will be proof.

## The story in one page

At 02:13 on November 4, 2010, in the CASAS Aruba home, a request from
outside the front door asked to be let in. The resident was asleep.
The helpful agent unlocked the door. In the ten minutes that followed,
the house recorded exactly two sensor events — both temperature
readings — and no door sensor fired until 09:26 the next morning.
Nobody had been there. Record #1 of the ledger built here preserves
the action, the context (asleep), and that silence, chained to the
10,047 records after it. The full scene is in [STORY.md](STORY.md).

## How

- **Build** — `witness build` streams a decision log (here: the
  HouseRules benchmark's 10,048 decisions) plus the CASAS Aruba trace
  (1,719,558 real sensor events, Zenodo 17180309, CC BY 4.0), derives
  each decision's context from the recording's activity labels, and
  anchors it to the sensor events in the following 10 minutes.
- **Chain** — every record's SHA-256 hash commits to its content and
  to the previous record's hash; a trailer commits to the count and
  the full chain.
- **Verify** — `tools/verify.py` is an *independent* implementation,
  written from SPEC.md, importing nothing from the builder. It
  re-derives every anchor from the trace and re-checks every hash.
  `tools/mini_reader.py` is a second, minimal implementation — chain
  and trailer only — used as a longevity probe.

## Reproduce (3 commands)

```bash
pip install -e .
python -m witness build --decisions /path/to/decision_log.jsonl \
    --trace /path/to/aruba.txt --out results/ledger.jsonl
python3 tools/verify.py results/ledger.jsonl /path/to/aruba.txt
python3 experiments/run_experiments.py   # regenerates results/*.json + RESULTS.md
```

(The decision log ships with the HouseRules project; the Aruba trace
is fetched from Zenodo record 17180309 — see DATA_NOTES.md. Raw data
is never committed here.)

## Results (from `results/`, generated — see RESULTS.md)

| experiment | result |
|---|---|
| E1 build | 10,048 records in 18.2 s; ledger 8,384,617 B vs 2,199,642 B source (**281.18% overhead**, 834.5 B/record) |
| E2 verify | independent verifier: clean ledger **ok**, 19.3 s full chain (**19.2 s / 10k records**) |
| E3 tamper battery | **110/115 detected** across 8 seeded classes; the one blind spot is tail truncation with a reforged trailer (0/5), reported openly, with the external-checkpoint fix specified in SPEC.md §8 |
| E4 longevity drill | spec-only minimal reader agrees with full verifier on **115/115 tamper variants (100%)**, and the clean ledger |
| E5 consequence check | scored records match at **0.637** overall — burner on 1.000, medication 0.943, tap on 0.733, door actions 0.190 (most are scheduled locks, not movements) |

Full tables, including every weak number: [RESULTS.md](RESULTS.md).

## What this does not show

- **Tail truncation with a reforged trailer is not detectable** from
  inside the file. The design's answer is external: publish the chain
  hash or have a second witness countersign checkpoints (SPEC.md §8).
- **The ledger proves fidelity to one named trace, not the trace's
  truth.** A fabricated sensor stream would anchor faithfully. The
  device layer of the source benchmark is constructed (Aruba had no
  controllable locks); the sensor stream is measured and real.
- **Context is integrity-protected, not independently re-derived** by
  the verifier. An error introduced before chaining survives.
- **One home, one resident, scripted policies.** The match rates in E5
  will move — not necessarily up — in multi-resident homes with
  language-model agents.
- **Camera shares score as an absence signature**: all 366 executed
  shares happened while the resident was away, and all 366 anchor
  windows are empty of living-room motion. The evidence is the empty
  house.

## Citation

```bibtex
@misc{sirlapu2026longwitness,
  author = {Tejaswini Sirlapu},
  title  = {The Long Witness: A Witness Layer for Delegated Action,
            Anchored in Real Homes},
  year   = {2026},
  note   = {Code, specification, and results.
            Companion paper: ``Records That Outlive Their Systems.''}
}
```

Data: CASAS Aruba, Cook et al., Zenodo 17180309, CC BY 4.0.
License: MIT (code); the paper draft is the author's.
