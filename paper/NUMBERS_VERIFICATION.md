# Numbers verification — "Records That Outlive Their Systems"

Every headline number in the paper, traced to its run-output file in
`../results/`. Timings are from the shipped run files (a measurement,
not a constant — reruns vary by seconds; the ledger content and all
counts are byte-identical across runs).

| paper claim | value | source file | field |
|---|---|---|---|
| decisions chained | 10,048 | e1_build.json | records |
| sensor events in trace | 1,719,558 | e1_build.json | trace_events |
| build time | 18.2 s (18.244) | e1_build.json | build_seconds |
| ledger size | 8,384,617 B | e1_build.json | ledger_bytes |
| source log size | 2,199,642 B | e1_build.json | source_decision_log_bytes |
| storage overhead | 281.18% | e1_build.json | overhead_pct |
| bytes per record | 834.5 | e1_build.json | bytes_per_record |
| verify verdict (clean) | ok = true | e2_verify.json | verdict.ok |
| verify time | 19.3 s (19.325) | e2_verify.json | verify_seconds_reported |
| verify per 10k records | 19.2 s (19.233) | e2_verify.json | per_10000_records_seconds |
| tamper cases total | 115 | e3_tamper.json | total_cases |
| alter_action | 20/20, 1.0 | e3_tamper.json | per_class.alter_action |
| delete_record | 20/20, 1.0 | e3_tamper.json | per_class.delete_record |
| reorder_records | 20/20, 1.0 | e3_tamper.json | per_class.reorder_records |
| alter_consequence | 20/20, 1.0 | e3_tamper.json | per_class.alter_consequence |
| forge_context | 20/20, 1.0 | e3_tamper.json | per_class.forge_context |
| truncate, trailer kept | 5/5, 1.0 | e3_tamper.json | per_class.truncate_tail_trailer_kept |
| truncate, trailer removed | 5/5, 1.0 | e3_tamper.json | per_class.truncate_tail_and_trailer |
| truncate + reforge trailer | 0/5, 0.0 (blind spot) | e3_tamper.json | per_class.truncate_and_reforge_trailer |
| detected overall | 110/115 | e3_tamper.json | sum of per_class |
| E4 clean-ledger mini verdict | ok = true | e4_longevity.json | clean_ledger_mini_ok |
| E4 agreement | 115/115, 1.0 | e4_longevity.json | agreements, agreement_rate |
| executed records | 9,294 | e5_consequence.json | executed_records |
| scored / matched / overall | 8,742 / 5,569 / 0.637 | e5_consequence.json | scored, matched, overall_match_rate |
| excluded (no signature) | 186 | e5_consequence.json | no_sensor_signature_excluded |
| front door fwd / prec / sym | 0.1902 / 0.2946 / 0.3987 (539/2,834 fwd) | e5_consequence.json | groups.front_door… |
| tap onset | 0.7328 (1,119/1,527) | e5_consequence.json | groups |
| tap cessation | 0.8005 (1,047/1,308) | e5_consequence.json | groups |
| med reminder | 0.9432 (1,461/1,549) | e5_consequence.json | groups |
| burner onset | 1.0 (1,089/1,089) | e5_consequence.json | groups |
| burner cessation | 0.7218 (314/435) | e5_consequence.json | groups |
| camera absence | 366 checked, 366 empty, 366 away | e5_consequence.json | absence_signature_groups |
| record #1 scene (02:13 unlock, 2 events, next door event 09:26:55) | — | results/ledger.jsonl seq 1 + trace scan | anchor of record 1 |

Source-benchmark figures quoted for context (policy names, 9,294/754
executed/refused split) trace to the HouseRules run outputs
(`decision_log.jsonl`, `results.json` in that project) and are labeled
as the companion benchmark's in the text.

One correction made during drafting, recorded here per house practice:
an early draft cited the first exploratory run's timings (build
19.9 s, verify 20.8 s). The shipped results files carry the final
run's timings (18.244 s / 19.325 s); the paper and README were updated
to the shipped files, and the deterministic figures (sizes, counts,
rates) are identical across both runs.
