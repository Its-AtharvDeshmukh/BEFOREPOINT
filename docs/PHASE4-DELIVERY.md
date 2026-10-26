# BEFOREPOINT — Phase 4 delivery

Implemented inside the existing project. No second application or hosted deployment was created. All intelligence remains explicitly simulated.

## 1. Existing project path

`/Users/atharvdeshmukhh/Documents/Codex/2026-10-25/let/outputs/sentinel-zero`

## 2. Reused components

FastAPI, immutable Event schema, Replay queue, BayesianFilter, source reliability, dependency grouping, cost matrix, existing VOI calculations, graph observations/dependencies, structural vulnerability inputs, SQLite receipt store, SSE state, scenario controls, React Query, shared panels/disclosures, Recharts, React Flow, MapLibre, MapTiler, Open-Meteo and Firebase configuration. Existing inference benchmark rows reproduce the saved baseline exactly.

## 3. New backend modules

`verification_catalog.py`, `prove.py`, `interventions.py`, `lifelines.py`, `flagship_api.py`, and `phase4_evaluation.py`. Small extensions add a validated verification-result event, normalized categorical evidence, a reusable graph-seed function, stream suppression, optional weather fields and separately hashed experiment records. The inference core and its original likelihoods/costs were retained.

## 4. New API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/lab/prove` | Six-candidate ranking, availability, outcomes and request status |
| POST | `/api/lab/prove/request` | Record a check against the displayed snapshot hash |
| POST | `/api/lab/prove/reveal` | Reveal an available response and apply it through Replay |
| POST | `/api/lab/cascade` | Paired, resource-constrained intervention comparison |
| GET | `/api/lab/lifelines` | Separate structure, hazard, coverage and uncertainty |
| POST | `/api/lab/lifelines/blackout` | Seeded six-of-ten stream disconnection |
| GET | `/api/lab/evaluation` | Frozen report from executed held-out experiments |

`/api/receipts` also exports experiment analyses anchored to forecast hashes. The existing forecast hash chain is preserved; experiment lifecycle records are separately hashed, not independently timestamped or part of that sequential chain.

## 5. PROVE ME WRONG

Six authorized synthetic instruments: independent water sensor, pump telemetry, out-of-band gateway diagnostic, existing camera, safe voluntary observation, independent traffic. Rankings reuse VOI loss calculations and subtract acquisition cost, delay harm and preparation-window penalties. Availability excludes dependent failed/unconfirmed gateways, unsupported camera power, already requested checks and checks that cannot return before replay end. The interface shows outcome probabilities/posteriors/actions, decision-change probability, expected and worst-case regret, and explains non-positive net value.

Requests have response times; outcomes are sampled only from physical facts realized by that response time. Ranking and filtering never accept the simulator's hidden future. Response application advances the shared replay one minute; late responses keep their original observation time. Duplicate requests/reveals are idempotent. Before/after comparisons disclose other simultaneous arrivals and hysteresis. Hypothetical outcome estimates hold the current state fixed, whereas actual replay also includes its transition and freshness handling.

## 6. CASCADE CUT

Four declared interventions plus monitoring: backup pump, emergency access, backup communications and inspection. Compare singles and two-action combinations under crew, pump and cost limits. Up to 2,048 bounded trials reuse identical seed activation, edge, preparation and side-effect draws for each plan. Costs, node disruption probabilities, total expected harm, paired net benefit and Monte Carlo intervals are exposed. Inspection alone has no invented preventive benefit. Emergency-access preparation includes alternate-road congestion as a side effect.

Timing sliders change whether preparation finishes before transmission. Last-useful-start estimates use the 20th percentile of baseline transmission time minus preparation, conditional on the relevant path; fewer than 20 relevant paths yields “timing uncertain.” This is a 24-minute simulation on a manually configured graph, not calibrated 72-hour forecasting or learned causality. Selecting a plan does not dispatch resources or change replay outcomes.

## 7. INVISIBLE LIFELINES

Three aggregate square cells with independent structure, fresh-coverage and reported-hazard layers. Each exposes access redundancy, backup power, service travel, essential dependencies, stream freshness and explicit unknown/conflicting reports. Exactly six of ten eligible synthetic streams disappear under the replay seed; later reports from disconnected streams are blocked. The nine sensor streams plus one gateway diagnostic include streams that have never reported; those remain unknown, not fabricated normal values.

Browser demonstration: River Quarter coverage fell from 50% to 0%, structural index stayed 0.965, and global hypothesis entropy fell from 1.700 to 1.624 bits. The UI explains why missingness can support a fault explanation without establishing hazard safety. Reset restores availability. Outputs contain synthetic area-level data, no individual identities or precise personal locations.

## 8. Frontend coverage

Command Center, Live Conditions, the three flagship workspaces, receipt inspection and Evaluation received substantive changes. The existing City Intelligence, Twin Test, Citizen Observations, Notifications, Integrations, Model & Assumptions and Settings retain the shared visual system and working flows. The three predecessor workbenches are merged rather than duplicated; old hash links remain compatible.

Command Center now surfaces eight distinct purposes: situation, hypotheses, next verification, response, source reliability, next failures, vulnerability and weather. Its recommendation moves before the narrative on phones. Graphs show baseline → intervention percentages and remain zoomable/selectable. Detailed mathematics stays expandable.

## 9. Reusable interface system

Existing Panel, Button, Badge, PageIntro, Disclosure, Stat, loading/error/empty states, accessible dialogs/tooltips and chart wrappers are reused. Added reusable verification/context briefs, candidate rows, metric tiles, paired comparisons, layer controls, stream cards and snapshot labels share the same spacing, palette, type scale and focus treatment. See [design research](PHASE4-DESIGN.md).

## 10. API integrations

Open-Meteo returned HTTP 200 with real current time, gusts, surface pressure and two daily forecasts. Visibility is taken from the matching provider hour when supplied. No historical averages were invented. Live weather never feeds the simulated crisis posterior. MapTiler integration and its existing public configuration are preserved. Firebase resource ID remains `sentinel-zero-c95fb`; client integration and server SDK are present, but trusted server credentials are absent, so actual push delivery remains unverified and no public warning was sent.

## 11. Automated verification

Baseline: 60 backend tests and 8 frontend tests passed before implementation. Final: **80 backend tests**, **13 frontend tests**, and production TypeScript/Vite build passed. Backend coverage includes temporal isolation, normalized outcome likelihoods, availability, contradictions, high costs/delay, action changes and unchanged actions, parallel preparation, duplicate protection, stale response time, paired simulation, insufficient resources, late preparation, side effects, missing seeds, dependency sensitivity, blackout reproducibility/suppression, structural independence, API integration and a full 19-receipt scenario.

The build retains its known large MapLibre chunk warning; the app code-splits map/chart/graph workspaces. A third-party TestClient deprecation warning is non-failing. No dependencies were added for Phase 4.

## 12. Actual baseline comparison

72 held-out scenario/seed/weather-regime combinations per policy; seeds 104729, 130363, 155921. One optional check at minute 4. The original policy chooses among its existing three checks when feasible; the new policy ranks six reliability-adjusted instruments. Both execute through the same physical-prefix sampler and replay pipeline.

| Policy | Crisis Brier ↓ | Mean episode loss ↓ | False alarms | Missed crises | Checks |
|---|---:|---:|---:|---:|---:|
| Unchanged engine | 0.1352 | 230.236 | 66.7% | 0.0% | 0 |
| Original check policy | 0.1333 | 226.006 | 66.7% | 0.0% | 36 |
| Prove Me Wrong | 0.1332 | 225.482 | 66.7% | 0.0% | 36 |
| 60% blackout | 0.1369 | 231.861 | 75.0% | 0.0% | 0 |

Episode loss is the sum of configured base action costs across 19 snapshots plus acquisition fees. It differs from the earlier benchmark's mean-per-minute decision cost. The new policy's loss is lower by **0.524** than the original check policy in this experiment; no statistical-significance or field-performance claim is made. Mean acquisition cost increased from 0.200 to 0.204; fee spent when the immediate action stayed unchanged also increased from 0.117 to 0.124. An unchanged immediate action does not by itself make a check unnecessary. Mean modeled crisis detection lead time is 8.0 minutes in this small synthetic set; missed-crisis rate alone conceals the high false-alarm rate.

Blackout worsened Brier, loss and false alarms; the interface reports this. The unchanged engine's original baseline rows match the saved results exactly. Cascade plans were selected using 256 trials, then evaluated with 512 independent draws under the same assumptions: resource feasibility 100%, mean modeled net benefit 7.727. This is model-based benefit, not validation against real interventions. Structural IoU after blackout is 1.000 on only three toy cells with manually declared fragility truth; preservation is intentional, not a representative spatial-performance result.

Raw results: [Phase 4 evaluation](phase4-evaluation.json), [original baseline regression](evaluation-phase4-regression.json), [API checks](phase4-api-checks.json).

## 13. Browser and responsive verification

Command Center and all three flagship pages were checked at **375, 430, 768, 1024, 1440 and 1920px**: 24 page/width combinations, no document-level horizontal overflow or fatal UI errors. All fourteen workspaces opened at 1440px. Browser actions verified mobile navigation, verification request/reveal/recomputation, insufficient crews, late preparation, six-of-ten blackout, structural preservation and the executed Evaluation report. Graph node comparisons rendered, maps/charts remained available, and the test tab reported zero console errors. Existing automated tests cover citizen consent, API failure presentation, notifications, loading/data-mode boundaries and shared-state updates.

[Machine-readable browser checks](phase4-browser-checks.json) and [screenshots](screenshots/phase4/) record the evidence. Compact graph labels may require zooming or the component selector on phones. These checks are not an exhaustive assistive-technology or cross-browser certification.

## 14. Remaining limitations

Synthetic likelihoods, structural weights, intervention effects and manually configured dependencies require calibration. Six checks are synthetic instruments; no municipal equipment or authorized camera feed is actually connected. Hypothetical VOI freezes other evidence while actual replay evolves. Intervention intervals represent sampling uncertainty under assumptions, not model misspecification. Three zones and a 24-minute laboratory do not solve the full official 2.2/2.3 scope. No federated learning, differential-privacy guarantee, re-identification defense, production authentication, independent audit timestamping or field validation is claimed. Dark theme only; genuine historical weather averages and actual Firebase push delivery remain unavailable.

## 15. Exact local run and verification commands

Dependencies are already installed on this machine. From a terminal:

```sh
cd "/Users/atharvdeshmukhh/Documents/Codex/2026-10-25/let/outputs/sentinel-zero"
SENTINEL_PYTHON="/Users/atharvdeshmukhh/Documents/Codex/2026-10-25/let/work/venv/bin/python" ./run.sh
```

The launcher builds the frontend and serves FastAPI on loopback. If another instance already owns port 8000, use that running instance or stop it before launching a replacement.

```sh
PYTHONPATH=backend "/Users/atharvdeshmukhh/Documents/Codex/2026-10-25/let/work/venv/bin/python" -m pytest -q
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

To reproduce the offline flagship benchmark:

```sh
PYTHONPATH=backend "/Users/atharvdeshmukhh/Documents/Codex/2026-10-25/let/work/venv/bin/python" -c 'import json; from sentinel.phase4_evaluation import evaluate_phase4; print(json.dumps(evaluate_phase4(), indent=2))'
```

## 16. Working local URL

[Open BEFOREPOINT](http://127.0.0.1:8000/)

Suggested demonstration: reset Twin A seed 26; request an independent check in PROVE ME WRONG; reveal when its response can arrive; inspect the posterior and receipt. Compare CASCADE CUT plans with two crews and one pump, then zero crews or a 24-minute delay. Reset and advance to minute 3, run the Lifelines blackout, and inspect coverage versus structure. Run Evaluation to see both the original benchmark and Phase 4's executed results.
