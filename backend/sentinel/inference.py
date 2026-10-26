from collections import defaultdict
import numpy as np
from .settings import CONFIG as C
from .reliability import source_scores, effective_reliability, dependency_key


class BayesianFilter:
    """Deterministic availability-time filter; takes observations, never scenario truth."""
    def __init__(self, gateway_aware=True, weighting=True, initial_betas=None):
        self.gateway_aware, self.weighting = gateway_aware, weighting
        self.initial_betas={source:tuple(beta) for source,beta in (initial_betas or {}).items()}

    def estimate(self, events, minute):
        visible = sorted((e for e in events if e.arrival_time <= minute and e.event_time <= minute),
                         key=lambda e: (e.arrival_time, e.id))
        # Resolve retractions using only currently available references.
        removed = {e.retracts for e in visible if e.kind == 'retraction'}
        active = [e for e in visible if e.id not in removed]
        p = np.array(C['prior'], dtype=float)
        trace = []
        citizen_seen = set()
        for t in range(minute + 1):
            available = [e for e in active if e.arrival_time <= t]
            scores = source_scores([e for e in visible if e.arrival_time<=t],self.initial_betas)
            monsoon = any(e.kind == 'baseline_shift' for e in available)
            prior = np.array(C['monsoon_prior'] if monsoon else C['prior'])
            p = C['transition_persistence']*p + (1-C['transition_persistence'])*prior
            groups = defaultdict(list)
            for e in active:
                if e.arrival_time == t and (e.kind in C['likelihoods'] or e.kind=='verification_result'):
                    if e.source_id.startswith('citizen:'):
                        if e.zone_id in citizen_seen: continue
                    r = effective_reliability(e, scores, self.weighting)
                    # Stale reports are less informative, never treated as current normality.
                    r *= np.exp(-0.12*(t-e.event_time))
                    if e.kind=='verification_result':
                        from .verification_catalog import outcome_likelihood
                        mixed=outcome_likelihood(e.payload['candidate_id'],e.payload['outcome'],r)
                    else:
                        likelihood = np.array(C['likelihoods'][e.kind])
                        # Unreliable component is hypothesis-independent contamination.
                        mixed = r*likelihood + (1-r)*.5
                    groups[dependency_key(e, self.gateway_aware)].append((e,np.log(mixed)))
            citizen_seen.update(e.zone_id for reports in groups.values() for e,_ in reports if e.source_id.startswith('citizen:'))
            logp = np.log(np.maximum(p, 1e-100))
            for key, reports in groups.items():
                # One effective log likelihood per common-cause group per minute.
                contribution = np.mean([v for _,v in reports], axis=0)
                logp += contribution
                if t >= minute-3:
                    trace.append({'minute':t, 'group':key, 'events':[e.id for e,_ in reports],
                                  'log_likelihood':contribution.tolist()})
            logp -= logp.max()
            p = np.exp(logp); p /= p.sum()
        return p, active, trace, source_scores(visible,self.initial_betas)
