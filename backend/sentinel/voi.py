import numpy as np
from .settings import CONFIG as C
from .decision import risks, cost_matrix


def value_of_information(p,deadline_rows,checks=None):
    p=np.array(p,dtype=float)
    now_matrix=cost_matrix(deadline_rows)
    baseline=float(min(now_matrix @ p))
    delay_rate=float(p @ np.array(C['delay_harm_per_minute']))
    options=[]
    for check in (C['checks'] if checks is None else checks):
        yes=np.array(check['positive']);u=check['inconclusive']
        expected=0.;wait_expected=0.;parallel_expected=0.;outcomes=[]
        future_matrix=cost_matrix(deadline_rows,check['delay'])
        parallel_matrix=cost_matrix(deadline_rows,.5*check['delay'])
        for name,likelihood in [('positive',(1-u)*yes),('negative',(1-u)*(1-yes)),('inconclusive',np.full(4,u))]:
            probability=float(p@likelihood)
            if probability<=0:continue
            posterior=p*likelihood/probability
            now_risks=now_matrix @ posterior
            future_risks=future_matrix @ posterior
            parallel_risks=parallel_matrix @ posterior
            expected+=probability*float(min(now_risks))
            wait_expected+=probability*float(min(future_risks))
            parallel_expected+=probability*float(min(parallel_risks))
            outcomes.append({'outcome':name,'probability':probability,'posterior':posterior.tolist(),
                'optimal_action':C['actions'][int(np.argmin(future_risks))],
                'parallel_action':C['actions'][int(np.argmin(parallel_risks))]})
        evsi=max(0.,baseline-expected)
        delay=check['delay']*delay_rate
        deadline_penalty=max(0.,wait_expected-expected)
        parallel_penalty=max(0.,parallel_expected-expected)
        net=evsi-check['cost']-delay-deadline_penalty
        parallel=evsi-check['cost']-.5*delay-parallel_penalty-.6
        options.append({**check,'expected_risk_after_check':expected,'evsi':evsi,'delay_harm':delay,
            'deadline_penalty':deadline_penalty,'parallel_deadline_penalty':parallel_penalty,
            'net_value':net,'parallel_net_value':parallel,'outcomes':outcomes})
    best=max(options,key=lambda x:max(x['net_value'],x['parallel_net_value'])) if options else None
    if best and max(best['net_value'],best['parallel_net_value'])>0:
        recommendation='Verify while preparing' if best['parallel_net_value']>best['net_value'] else 'Verify first'
        selected=best['id']
    else:
        recommendation='Prepare now' if int(np.argmin(risks(p,deadline_rows)))>0 else 'No further evidence needed'
        selected=None
    strategies=[{'id':'verify_first','label':'Verify first','expected_cost':min((baseline-c['net_value'] for c in options),default=None)},
        {'id':'prepare_now','label':'Prepare immediately','expected_cost':float(min((now_matrix @ p)[1:]))},
        {'id':'parallel','label':'Verify while preparing','expected_cost':min((baseline-c['parallel_net_value'] for c in options),default=None)},
        {'id':'no_check','label':'No additional verification','expected_cost':baseline}]
    return {'strategies':strategies,'recommendation':recommendation,'selected_check':selected,'baseline_risk':baseline,
        'delay_harm_rate':delay_rate,'checks':options,
        'explanation':'EVSI = current minimum expected loss − expected posterior minimum loss. Net value subtracts acquisition cost, per-state delay harm, and increased expected loss from reduced preparation effectiveness. The latter is weighted by forecast event probability. Parallel preparation halves the start delay and adds 0.6 mobilization units. All parameters are illustrative.'}


def counterfactual_check(p,check,outcome):
    """Condition only on a supplied check outcome; accepts no hidden state."""
    positive=np.array(check['positive']);u=check['inconclusive']
    likelihood={'positive':(1-u)*positive,'negative':(1-u)*(1-positive),'inconclusive':np.full(4,u)}[outcome]
    posterior=np.array(p)*likelihood
    if posterior.sum()<=0:raise ValueError('Impossible observation under the supplied check model')
    return posterior/posterior.sum()
