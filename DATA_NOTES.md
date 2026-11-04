# Data notes — provenance and what was verified

## Sources (both real, both already public or published with this work)

1. **CASAS Aruba trace** — Zenodo record **17180309**, "CASAS Smart Home
   dataset (aruba, cairo, milan, tulum)", creator Diane Cook,
   **CC BY 4.0** (license read from the record's own metadata).
   File `aruba.txt`: **1,719,558 rows**, 2010-11-04 to 2011-06-11,
   41 sensors, 11 activity labels. MD5
   `7ed6bc9066f740396fbe49796ab98459` — matches the checksum published
   on the Zenodo record. Attribution: Cook, D., Crandall, A., Thomas,
   B., & Krishnan, N. (2013). "CASAS: A Smart Home in a Box."
   *IEEE Computer*, 46(7), 62–69.
2. **HouseRules decision log** — `results/decision_log.jsonl` from the
   HouseRules benchmark (companion project): **10,048 decisions** made
   by three scripted agent policies replayed against the Aruba
   recording (9,294 executed, 754 refused). The raw trace is not
   committed to this repository; fetch it from the Zenodo record above.

## Measured vs constructed (the standing honesty note)

- **Measured:** every sensor event, timestamp, and activity label in
  the trace; every decision, action, and gate outcome in the decision
  log; every number in RESULTS.md, which is generated from run outputs
  in `results/`.
- **Constructed:** Aruba had no controllable locks, cameras, or alarms,
  so the decision log's device actions are a documented benchmark
  construction (see HouseRules). The witness layer treats that log as
  its input record stream — the same role a real agent's audit log
  would play. Consequence anchors bind those decisions to the
  *measured* sensor stream, which is real.
- **Derived:** sensor zones (kitchen / living / bedroom) are computed
  from the recording itself — the eight motion sensors firing most
  inside episodes with the relevant activity label (Meal_Preparation,
  Relax, Sleeping). No floor plan was consulted; the zones are
  data-derived heuristics and are labeled as such wherever used.
