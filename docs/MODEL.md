# BEFOREPOINT model assumptions and limits

Version `beforepoint-0.2-illustrative`. Every configured number is a manually selected demonstration assumption, not validated emergency policy. No LLM supplies probabilities, and no future label is an estimator input.

## Bayesian inference

Exactly four hypotheses: NOISE, SENSOR_FAILURE, ISOLATED_INCIDENT, CASCADING_CRISIS. Each minute, predict `p_prior = 0.94 p_previous + 0.06 baseline`. An available monsoon signal selects the alternative background distribution from its arrival onward.

For a newly available report, effective reliability is `min(declared quality, source Beta mean) × exp(-0.12 arrival delay)`. The likelihood is `r × configured likelihood + (1-r) × 0.5`. Report detectors are not mutually exclusive categorical events. Source/correlation/gateway groups contribute their average log likelihood once per minute. Max-shifted exponentials normalize the four-state distribution stably.

Citizen reports contribute only in the first available batch per zone per run. This deliberately conservative cap prevents cross-minute copies from accumulating, but ignores legitimate later citizen updates. Unknown coordination across apparently unrelated channels remains a limitation. Silence is never a generated normal reading.

Reports are processed at availability time. Retractions remove their inference contribution on deterministic reconstruction, while historical receipts remain unchanged. Source adjudications remain quality evidence even if the underlying observation is later withdrawn. No future event or hidden outcome is supplied to inference.

## Cross-episode source adaptation

A source starts from Beta(8,2). Only explicit operator adjudication increments success/failure counts. The first judgment per run/report counts once. SQLite stores the ledger. Each replay copies its source-prior snapshot at construction; later learning cannot affect that replay's earlier decisions. Within a run, adjudication affects subsequent observations, not a retroactive rewrite of previously available likelihoods. The snapshot is included in receipts and private run metadata.

The local operator endpoint is trusted only for the demonstration. Production adjudication requires authentication, provenance and governance. Agreement with the model or a hidden simulated outcome never automatically becomes a source label. Held-out benchmark episodes use independent stores; no test label updates reliability.

## Expected-cost actions and operational lead time

The four rows of the configured cost matrix represent WATCH, PREPARE, ALERT, ESCALATE. Columns are the four hypotheses. `base_loss(a) = C_a · p`.

For a preparation aimed at a forecasted failure, independent uniform failure and response intervals give conditional effectiveness `P(start + response ≤ failure)` on an 81×81 grid. The event-probability-weighted miss mass is `P(event) × (1-effectiveness)`. Preparations currently address the same forecast target, so the model takes the largest miss mass rather than summing them as independent hazards.

The effective matrix adds `miss_mass × outer(action_lead_time_weights, lead_time_consequences)`. These vectors are explicit illustrative assumptions in config. This separates false-alarm/operational costs from reduced preparation effectiveness. Expected total cost selects the minimum, with a 0.7-unit switching margin and a two-minute hold on downgrades. Base and lead-time losses are exposed separately in API decisions.

## ACT OR VERIFY

Each imperfect check has state-conditional positive likelihood, an inconclusive probability, delay and acquisition cost. For outcome o, calculate `P(o)`, Bayesian `p(h|o)`, and the posterior-optimal action loss using the same effective matrix.

`EVSI = min_a loss_now(a,p) − Σ_o P(o) min_a loss_now(a,p|o)`.

The deadline penalty is the increase in integrated posterior minimum loss when preparation starts after the check delay. Because the effective matrix uses event probability, a rare forecast does not carry the same timing penalty as a likely event. Additional configured per-state delay harm and acquisition costs are subtracted from EVSI. Parallel preparation uses half the start delay, half the additional delay harm, and a 0.6-unit mobilization cost. This is an explicit one-step approximation, not complete intervention optimization. VOI uses unconstrained minima; displayed action stability is handled separately.

The best positive-net strategy is selected; otherwise preparation or no further verification is recommended. Checks do not synthesize outcomes. The API `/api/analysis/verify` accepts explicit normalized probabilities and bounded optional check specifications for sensitivity analysis without mutating simulation state.

## Infrastructure and structural consequences

Nine nodes and eight manually specified dependencies define the demonstration graph. Recent observations seed local hazards; a healthy reading clears only its own zone's corresponding seed. Learned reliability influences seed confidence. Strongest acyclic paths generate specific component-disruption predictions with probabilities, time windows, support IDs and assumptions. This is not a learned causal model or a complete city-wide event distribution. Forecast horizons are seeded from recent reported conditions, not a precisely identified physical onset.

The 80% preparation deadline is the 20th percentile of failure time minus response time, conditional on the predicted event. It is a model-estimated action start window, never a guaranteed last safe moment.

Zone consequence index: `min(1, .45/(1+routes) + .2×no_backup_power + .35×min(1,facility_minutes/20))`. It does not modify incident probability. Fresh and missing sources are shown separately. There is one city-wide hypothesis posterior, not independently calibrated zone hazard probabilities. Aggregate data does not implement federated learning or full Problem 2.3 compliance.

## Persistence and audit

SQLite stores incoming observations, complete minute receipts, source metadata and adjudications, run/scenario/model snapshots, and evaluation results. Hidden scenario outcomes and schedules are saved only in private run metadata; no ordinary state/diagnostic API returns them before an explicit gated reveal. The estimator receives observations/minute and its frozen source prior, not database metadata.

Canonical JSON plus SHA-256 links each receipt to the previous one. Receipts include model/configuration hashes, visible and active event IDs, probabilities, costs/action, forecasts, supporting reports and source priors. This detects edits relative to the stored chain; an administrator can rebuild it. It proves no external timestamp or administrative tamper resistance. Replay tests separately enforce temporal isolation.

## Evaluation interpretation

See `BACKEND-ACCEPTANCE.md` and `evaluation.json` for actual results. Crisis Brier targets the eventual episode label at each minute; calibration bins compare average predicted probability with observed eventual-outcome frequency. False alarms mean any ALERT/ESCALATE in a non-cascade episode, including isolated incidents for which ALERT can be rational. Delay is relative to synthetic onset at minute 10, floored at zero; misses are penalized through episode end+1.

The historical base decision-cost metric uses the original static matrix against withheld episode truth for all policies. Candidate forecast Brier scores only emitted component/window pairs against the hidden schedule. It is not all-node calibration. Baselines emit no infrastructure forecasts. The one-shot paired verification trial separately uses the effective matrix and actual configured delay/check costs; it samples an imperfect observation from a withheld class in the evaluator, then gives only that outcome and the prior to the policy. It does not change the simulated infrastructure or establish multi-step utility.

The Bayesian model does not dominate false alarms, switching or every ablation. The current scientific limitations remain visible. No structural repair was fitted to maximize the reported test results.

## External context and operational boundary

Open-Meteo values are weather-model estimates, never automatically crisis evidence. MapTiler supplies a basemap; every sensor/facility/zone overlay is simulated. FCM is opt-in, test-only, and requires an authorized server credential for real sends. No public emergency broadcasts occur.

This local single-worker prototype has no production authentication or persistent running-state recovery. Source priors and audits persist; a server restart creates a new simulation run. Field calibration, validated costs, real sensor integrations, stronger adversarial defenses, production authorization, and official PDF compliance remain outside this milestone. The referenced organizer PDF was not supplied.
