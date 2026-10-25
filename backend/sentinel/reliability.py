from collections import defaultdict
from .models import Event


def source_scores(events: list[Event], initial_betas=None):
    """Beta(8,2), updated only by explicit independent operator adjudications."""
    scores = defaultdict(lambda: [8., 2.])
    for source,beta in (initial_betas or {}).items():
        scores[source]=list(beta)
    by_id = {e.id: e for e in events}
    judged = set()
    for e in sorted(events, key=lambda x: (x.arrival_time, x.id)):
        if e.kind == 'verification' and e.retracts in by_id and e.retracts not in judged:
            report = by_id[e.retracts]
            if report.kind in ('verification', 'retraction'):
                continue
            judged.add(e.retracts)
            scores[report.source_id][0 if e.payload['correct'] else 1] += 1
    return {k: a/(a+b) for k,(a,b) in scores.items()}


def effective_reliability(e, scores, weighting=True):
    return min(e.reliability, scores.get(e.source_id, .8)) if weighting else 1.


def dependency_key(e, gateway_aware=True):
    if e.source_id.startswith('citizen:'):
        return f'citizen:{e.zone_id}'
    if e.correlation_group:
        return f'group:{e.correlation_group}'
    if gateway_aware and e.gateway:
        return f'gateway:{e.gateway}'
    return f'source:{e.source_id}'
