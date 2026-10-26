# Event contract and temporal isolation

All events use `sentinel.models.Event` (Pydantic, extra fields rejected).

| Field | Meaning |
|---|---|
| `id` | Unique report identity, 1–120 characters. Exact duplicate is ignored; conflicting reuse is rejected. |
| `source_id` | Source identity. `operator` is required for explicit adjudication. |
| `kind` | Validated enumerated observation type. See `/api/config` likelihoods and the control events below. |
| `zone_id` | `north`, `river`, or `east` (synthetic zones). |
| `event_time` | Integer simulated minute when observed; 0–10000. |
| `arrival_time` | Integer minute when available; cannot precede `event_time`. |
| `reliability` | Declared observation quality in [0,1], upper-bounded by learned source mean. |
| `gateway` | Optional shared gateway identifier. |
| `correlation_group` | Optional explicit common-origin identifier. Takes precedence over gateway. |
| `payload` | Optional observation details; no hidden episode label is passed to inference. |
| `retracts` | Existing observation ID required for a retraction or verification. |

Example judge submission at current minute 3:

```json
{"id":"judge-water-1","source_id":"independent-level","kind":"water_high","zone_id":"river","event_time":3,"arrival_time":4,"reliability":0.85,"gateway":null,"payload":{}}
```

POST this to `/api/events`. Submitted reports take effect on the next simulated minute; event time can be earlier. The replay engine rejects reports whose arrival/event time is still in the future. A duplicate matching the original is idempotent. A conflicting ID never replaces the original.

Control events:

- `retraction`: `retracts` references an already available observation. At the next decision, the filter deterministically replays all available history excluding the retracted observation. Old forecast receipts are unchanged.
- `verification`: `source_id="operator"`, `retracts` references an available observation, and `payload={"correct":false}` (or true). The first adjudication for a report updates its source's Beta prior; duplicates do not count again. This is a trusted local judge control, not a claim that the report's truth was inferred independently.
- `baseline_shift`: an available operator/weather regime signal switches the transition baseline to the monsoon prior. It does not change historic decisions.

The simulator contains an immutable tuple of events plus a separate hidden outcome label and failure schedule. The Bayesian engine accepts only `(events, minute)`; it has no scenario-name, hidden-label, or future-schedule input. It also filters availability defensively. Twin prefixes match byte-for-byte through minute 7, including source, timestamp and quality fields; divergence begins at minute 8.

Every new minute records the IDs of all visible reports and the active (nonretracted) subset. Event time and arrival time are shown separately when delayed. Reports arrive once; no new healthy observation is created because a stream is silent. Older reports weaken at first ingestion by `exp(-0.12 × arrival_delay)` and the state transition gradually returns the posterior toward the baseline afterward.

## Phase 4 verification responses and blackout

`verification_result` is a synthetic instrument observation, distinct from an operator's `verification` adjudication. It requires a catalog `candidate_id`, one of `positive`, `negative`, `inconclusive`, and the catalog's `check:<id>` source. The filter uses the catalog's normalized categorical likelihood and effective source reliability. `/api/lab/prove/request` records a snapshot-anchored ticket; `/api/lab/prove/reveal` is the supported execution path. Revealing applies the event on the next shared replay minute, once that minute can receive the response. Sub-minute nominal delays round up to this one-minute grid. A late reveal preserves the original response time so freshness decay applies. Repeating reveal never adds another report.

The blackout selects exactly six of the ten declared eligible synthetic streams with a deterministic seed. It queues explicit `stream_missing` observations under the common `blackout:network` correlation group, then suppresses subsequent measurements from those streams. Newly submitted measurements from disconnected stream IDs are rejected. Existing available evidence remains in history; known structure is preserved. Resetting the scenario restores configured availability without inventing normal readings. Independent verification instruments, voluntary observers and live weather are not eligible blackout streams.
