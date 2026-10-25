"""Expected configured losses with conditional preparation-effectiveness costs."""
import numpy as np
from .settings import CONFIG as C


def deadline_miss_mass(deadlines, delay=0.):
    # Preparations protect the same forecast event: take the worst effectiveness loss,
    # rather than summing correlated opportunities as independent failures.
    masses=[]
    for row in deadlines or []:
        if 'failure_window' not in row:continue
        failure=np.linspace(*row['failure_window'],81)
        response=np.linspace(*row['response_minutes'],81)
        start=row['decision_minute']+delay
        effectiveness=float(np.mean(start+response[None,:]<=failure[:,None]))
        masses.append(row['event_probability']*(1-effectiveness))
    return max(masses,default=0.)


def cost_matrix(deadlines=None,delay=0.):
    base=np.array(C['costs'],dtype=float)
    lead=deadline_miss_mass(deadlines,delay)*np.outer(C['action_lead_time_weights'],C['lead_time_consequences'])
    return base+lead


def risks(p,deadlines=None,delay=0.):
    return cost_matrix(deadlines,delay) @ np.array(p)


def decide(p,previous=None,minutes_since_change=99,deadlines=None):
    base=np.array(C['costs']) @ np.array(p)
    loss=risks(p,deadlines)
    best=int(np.argmin(loss));held=False
    if previous in C['actions']:
        old=C['actions'].index(previous)
        if best!=old and (loss[old]-loss[best]<C['hysteresis_margin'] or
                          (best<old and minutes_since_change<C['downgrade_hold_minutes'])):
            best,held=old,True
    return {'action':C['actions'][best],'expected_cost':float(loss[best]),
            'costs':dict(zip(C['actions'],loss.tolist())),
            'base_costs':dict(zip(C['actions'],base.tolist())),
            'lead_time_costs':dict(zip(C['actions'],(loss-base).tolist())),
            'deadline_miss_mass':deadline_miss_mass(deadlines),
            'held_by_hysteresis':held,
            'reason':'Minimum expected configured loss, including forecast-probability-weighted preparation effectiveness, subject to switching margin and downgrade hold.'}
