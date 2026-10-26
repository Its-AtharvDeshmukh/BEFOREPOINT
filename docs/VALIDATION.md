# Validation record

Validated locally on 25 October 2026 with Python 3.13.2 and Node.js 22.19.0. Exact Python package versions are in `backend/requirements-lock.txt`; Node versions are locked by `frontend/package-lock.json`.

- **37 pytest tests passed.** One upstream Starlette warning says its httpx TestClient integration is deprecated; the tests still pass.
- **React production build passed**, including strict TypeScript compilation.
- The real FastAPI app was started on loopback, serving the compiled dashboard and assets with HTTP 200.
- Browser validation confirmed: Step changes simulated minute, probabilities, forecasts and events; Run changes to Pause; Twin Test renders both calculated histories and passes the identical-prefix/revision checks; evaluation renders all model rows and the counterfactual verification-policy result; receipt inspection reports a valid hash chain; a safe citizen submission queues a report at the next minute.
- Backend API tests cover citizen deduplication, event validation, fault injection, report-reference validation, reset, start/pause, replay, receipt persistence and Twin Test.
- Engine tests cover all 12 scenarios, normalization, identical twin prefixes over multiple seeds, future and delayed information exclusion, duplicate idempotence, 100 shared-gateway reports, cross-minute citizen amplification limits, retractions preserving historical receipts, adjudication reliability, cost selection and hysteresis, graph-specific forecasts, deadline probability, value-of-information equations, missing zones, tamper detection, reproducibility, configuration hashes, and one-shot check-policy repeatability.
- The frozen benchmark was actually run across **72 episodes per model** for five models. Results are saved in `evaluation.json` and available through `/api/evaluation`.

## Results worth scrutinizing

Bayesian crisis Brier: 0.137; fixed threshold: 0.171; event counting: 0.231. However, Bayesian cascade-specific episode false-alarm rate is 0.667 versus 0.500 and 0.375, and its average action changes are 2.847 versus 1.500 and 1.167. It has better probability scoring but does not dominate every operational measure. The gateway-unaware ablation has lower synthetic decision cost in this sample. No held-out result was used to retune parameters.

The sampled one-shot verification policy at minute 7 requested checks in 18/72 trials. Mean policy loss is 17.390 versus 17.083 with no check; realized mean benefit is **−0.307**. This limited trial does not establish a benefit from verification, despite positive expected values under some inferred posteriors. See `MODEL.md` for scope and assumptions.

## Not validated

Real-world calibration, official PDF compliance, field safety, adversarial security, production concurrency, cross-worker state sharing, production authentication, long-horizon reliability, and multi-step intervention utility. No public emergency notification was sent. No external municipal sensor data was used. No production deployment was attempted: the requested deliverable is local.
