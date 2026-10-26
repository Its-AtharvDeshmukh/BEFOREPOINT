# BEFOREPOINT — implementation audit (before acceptance repair)

Existing project: `/Users/atharvdeshmukhh/Documents/Codex/2026-10-25/let/outputs/sentinel-zero`.

React 19 + TypeScript/Vite frontend; Python/FastAPI/Pydantic/NumPy backend; SQLite audit storage. A single local API serves the compiled UI at 127.0.0.1:8000, with SSE simulation updates. Existing Python import paths, SQLite identifiers, environment names, and Firebase project `sentinel-zero-c95fb` are retained for compatibility. No MANDATE project is used.

## Fully implemented at audit

- Four-state normalized Bayesian filter, arrival-time isolation, duplicate identity handling, explicit common-source grouping, retraction reconstruction, regime-shift prior signal.
- Explicit four-action cost matrix and action hysteresis.
- Seeded simulator with twelve scenarios and an independent hidden-label/failure schedule.
- Independent Twin Test with identical minute 0–7 visible prefix; interactive controlled twin replay and reveal API.
- Imperfect-check one-step expected value of information, including inconclusive outcomes and a parallel-preparation approximation.
- Nine-node configured infrastructure graph, next-event forecasts, uniform-delay conditional preparation deadlines.
- Three-zone aggregate consequence assessment and missing-stream status.
- SQLite observations, per-minute posterior/decision/forecast receipts, hash chaining, prior-run inspection.
- Synthetic held-out evaluation against two baselines and two ablations; calculated calibration bins and a one-shot verification-policy comparison.
- Citizen submission through the same ingestion path; conservative rumor/citizen evidence cap.
- Cached Open-Meteo adapter; MapTiler/MapLibre basemap; Firebase public initialization, bundled messaging worker, token storage/opt-out and optional server sender.

## Partial implementations / gaps requiring repair

1. Source reliability is updated from explicit adjudications within an episode, but not carried across episodes. A persisted source prior snapshot is needed, fixed at each replay's start to prevent retroactive leakage.
2. The decision cost matrix is explicit, but operational lead time is only reflected indirectly in the separate verification model. Expected loss must include a documented preparation-effectiveness component.
3. ACT OR VERIFY considers time windows but its missed-window penalty does not explicitly weight the forecast event probability. It needs a consistent expected-loss context shared with action selection.
4. Hospital activity is represented through a generic traffic event in one scenario. Explicit hospital and dispatch observation types are needed.
5. Forecasts omit structured supporting observation IDs; a healthy reading in one zone can clear a city-wide hazard seeded by another zone.
6. Scenario definitions and evaluation results are file-backed or in memory, rather than versioned in SQLite. Model/scenario snapshots and evaluation records should also be persisted.
7. A dedicated callable verification-analysis API and backend diagnostics endpoint are absent.
8. Weather adapter checks only broad current/hourly presence. Missing provider variables/array inconsistencies require stronger validation.
9. Backend FCM sending is implemented but cannot be exercised without an authorized server service-account credential. No such credential was supplied; actual push delivery is not verified.

## Bugs and integration findings

- A MapLibre 6 module worker initially failed to load after the security update. Explicit Vite worker bundling fixed it; the geographic basemap and selectable simulated markers were subsequently verified in browser.
- A frontend direct `/citizen` route ignored subsequent hash navigation. Its route resolver has been corrected; it needs final browser revalidation.
- Rebuilding assets while an older page was open caused stale lazy-chunk errors. The new build includes bounded reload recovery; final console validation remains necessary.
- The package audit initially identified a MapLibre sanitizer issue and an unused Firestore/gRPC transitive dependency issue. Updated MapLibre and a patched gRPC override now give zero npm audit findings.

## Test baseline

44 backend tests pass; none fail. This includes 37 original engine/API tests plus seven new weather, twin-control, notification-registration, request-isolation, outcome-gating and calibration tests. Tests cover core functionality but did not yet prove the cross-episode or lead-time requirements above. A passing test count alone is not completion of the acceptance gate.

Frontend TypeScript, worker type checks, and production build pass. Browser checks have verified weather values and attribution, map loading/markers/layers, verification calculations, synchronized twins through minute 7 and explicit reveal after minute 8, citizen request creation and API-confirmed submission. Full responsive and all-page verification is still pending.

## Integration status

- Open-Meteo: actual current/hourly provider response received through the cached API. Live weather does not enter crisis inference.
- MapTiler: dark and street style endpoints returned HTTP 200 with the supplied key; a geographic basemap rendered at the local origin. Account allowlist and eventual deployed origin are not available to the client and are not claimed verified.
- Firebase: public web/VAPID configuration present in ignored local environment; browser support detected; messaging worker served as JavaScript. Token registration/opt-out tested through API with test registrations. Actual browser permission/token acquisition and real send delivery remain unverified. Trusted service-account credentials are missing.
- Optional LLM, MongoDB and real municipal sensors: disabled/not configured, explicitly shown as such.

## Static/synthetic content

Priors, likelihoods, costs, graph edges, city-centre placements and structural zone attributes are manually configured simulation assumptions. Model outputs are calculated, not dashboard fixtures. Weather is fetched; no fake provider fallback exists. The prototype does not claim real sensors, learned causal links, field accuracy, federated learning, external timestamp proof, or automatic real emergency warnings.
