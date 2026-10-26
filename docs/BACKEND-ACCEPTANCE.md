# BEFOREPOINT backend acceptance gate

Gate run: 25 October 2026. Model: `beforepoint-0.2-illustrative`.

**60 tests passed, zero failed.** One upstream Starlette/httpx deprecation warning remains. All mandatory local proof-of-concept acceptance cases below are covered. This gate is functional verification on synthetic data, not scientific or emergency-service certification. Trusted FCM delivery remains an optional integration blocker and does not block the offline engine.

| Requirement | Verified implementation / tests |
|---|---|
| 1. Normal probabilities | All twelve scenarios normalize each minute, including normal rain |
| 2. Developing crisis | Flood and twin crisis produce changing calculated posteriors |
| 3. Duplicates | Ingest identity idempotence; conflicting IDs rejected; citizen copy cap |
| 4. Shared gateway | 100 reports equal one group under normal, crisis and contradictory contexts |
| 5. Delays / no leakage | Future arrivals excluded; estimator has observation/minute input only |
| 6. Retractions | Current inference reconstructs; earlier receipts remain unchanged |
| 7. Source adaptation | Explicit adjudication updates Beta reliability, persists to later episodes, cannot rewrite earlier priors |
| 8. Prior shifts | Monsoon regime signal affects the filter only after arrival |
| 9. Four action costs | Explicit base matrix plus documented expected preparation-effectiveness loss |
| 10. Stability | Switching margin and downgrade hold tested for small and material changes |
| 11. Three forecasts | Components, event types, probabilities, windows, support IDs and assumptions tested |
| 12. Twin identity | Identical prefix through minute 7 across multiple seeds; evidence-driven divergence |
| 13. Adversarial cases | Rumors, duplicates, delayed calls, camera/gateway loss and conflicting reports run without failure |
| 14. Genuine VOI | Bayes outcome expectation; quality/cost/delay sensitivity; event-probability-weighted delay penalty |
| 15. Real metrics | Actual held-out replay benchmark, calibration bins and paired check policy calculated |
| 16. Receipts | SQLite persistence, hash verification and deliberate tamper detection |
| 17. APIs | Diagnostics, analysis, decisions, replay, twin controls, receipts and typed error responses |
| 18. Critical end-to-end | Validated judge event queued and processed through API |
| 19. Citizen pipeline | Opt-in response queued, deduplicated, then included in simulation evidence |
| 20. Optional APIs | Weather failures/rate cooldown do not prevent core replay |

## Repairs made before the gate

- Persisted source reliability ledger and per-run immutable source-prior snapshots. Adjudications are deduplicated by run and target observation. No outcome label trains source quality.
- Shared action/verification expected-cost context uses forecast event probability and conditional response effectiveness. Base cost and lead-time loss are separately exposed.
- VOI integrates positive, negative and inconclusive outcomes and computes the increased expected decision loss after a delayed check. Parallel preparation uses a half-delay approximation and explicit mobilization cost.
- Explicit hospital activity and dispatch-delay observations. Forecasts include supporting report IDs, event types, assumptions and uncertainty; healthy readings clear only the matching zone hazard seed.
- SQLite scenario/model/run metadata, evaluation persistence, backend diagnostics, and a separately callable verification sensitivity endpoint.
- Provider variable/array validation and Open-Meteo rate-limit cooldown with stale-cache or explicit unavailable responses.
- Shared SQLite lock between audit and notification adapters. Failed optional push delivery no longer hides successful in-app request creation.

## Actual calculated benchmark

72 episodes/model; twelve scenarios; seeds 104729, 130363, 155921; original and shifted regimes. Parameters were specified for these structural repairs before recalculating results; they were not fitted to the reported outcomes.

| Model | Crisis Brier ↓ | Cascade false-alarm rate ↓ | Detection delay (min) ↓ | Base decision cost ↓ | Action changes | Candidate forecast Brier ↓ |
|---|---:|---:|---:|---:|---:|---:|
| Bayesian | 0.1352 | 0.6667 | 0.0000 | 12.1177 | 2.8056 | 0.1438 |
| Fixed threshold | 0.1709 | 0.5000 | 0.0000 | 12.7061 | 1.5000 | Not emitted |
| Event count | 0.2311 | 0.3750 | 0.0000 | 17.1184 | 1.1667 | Not emitted |
| No gateway grouping | 0.1363 | 0.6667 | 0.0000 | 11.4145 | 3.0972 | 0.1375 |
| No reliability weights | 0.1403 | 0.7292 | 0.0000 | 12.8787 | 3.0278 | 0.1482 |

Twin consistency: PASS. The one-shot sampled verification policy requests checks in 42/72 trials: mean no-check loss 17.5532, policy loss 15.4385, realized mean benefit 2.1148 configured units. These use a synthetic observation model and do not establish field or multi-step intervention benefits.

Probability scoring improves over both baselines, but false alarms and switching are higher. The gateway-unaware ablation has lower base decision cost and candidate forecast Brier in this sample. Those results are retained. Zero detection delay reflects early ALERT/ESCALATE relative to the fixed synthetic onset; it does not mean perfect detection accuracy. Forecast scores are conditional on emitted candidates, not a complete calibration measure.

Exact data: `evaluation.json`. The dashboard exposes these calculated outputs directly. The base decision-cost metric deliberately reports the original static matrix loss for all models; the separately disclosed lead-time costs guide the revised policy and are included in the one-shot check-policy trial, not silently added to that historical metric.
