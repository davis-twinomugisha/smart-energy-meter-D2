"""Conditional balance calculations. Balances here are supplied scenarios, not utility data."""
from datetime import timedelta
import numpy as np
from .features import validate_history,make_features,parse_time

HORIZON_HOURS=24

def exhaustion_time(energy,balance_kwh):
    if isinstance(balance_kwh,bool):raise ValueError('balance must be numeric')
    b=float(balance_kwh)
    if not np.isfinite(b) or b<0:raise ValueError('balance_kwh must be finite and nonnegative')
    a=np.asarray(energy,dtype=float)
    if a.ndim!=1 or not np.isfinite(a).all() or (a<0).any():raise ValueError('energy must be finite and nonnegative')
    if b==0:return 0.0
    total=0.0
    for i,e in enumerate(a):
        if e>0 and total+e>=b:
            return float(i+(b-total)/e) # uniform consumption within the crossing hour
        total+=e
    return None # not exhausted inside supplied horizon, not an extrapolated precise time

def forecast_path(model,history,start,horizon=HORIZON_HOURS):
    if horizon<1 or horizon>24:raise ValueError('horizon must be 1 through 24 hours')
    a=validate_history(history).tolist()
    t=parse_time(start) if isinstance(start,str) else start
    forecasts=[]
    for j in range(horizon):
        value=float(model.predict(make_features(a[-24:],t+timedelta(hours=j)).reshape(1,-1))[0])
        value=max(0.0,value)
        forecasts.append(value);a.append(value)
    return forecasts

def baseline_paths(history):
    a=validate_history(history)
    return {'mean_24h':np.full(24,a.mean()).tolist(),
            'persistence':np.full(24,a[-1]).tolist(),
            'same_hour_yesterday':a.tolist()}
