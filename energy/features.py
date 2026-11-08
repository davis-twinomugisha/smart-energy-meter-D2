"""Causal features. History is exactly 24 completed hourly energy totals, oldest first."""
from datetime import datetime
import math
import numpy as np

FEATURE_NAMES = ['lag_1','lag_2','lag_3','lag_6','lag_12','lag_24',
                 'mean_3','mean_6','mean_24','std_24',
                 'hour_sin','hour_cos','weekday_sin','weekday_cos','weekend']

def validate_history(history):
    a=np.asarray(history,dtype=float)
    if a.shape!=(24,) or not np.isfinite(a).all() or (a<0).any():
        raise ValueError('history_kwh must contain exactly 24 finite, nonnegative hourly values, oldest first')
    return a

def parse_time(value):
    if not isinstance(value,str):raise ValueError('forecast_start must be an ISO date/time string')
    try:t=datetime.fromisoformat(value.replace('Z','+00:00'))
    except (ValueError,TypeError):raise ValueError('forecast_start must be a valid ISO date/time')
    if t.minute or t.second or t.microsecond:raise ValueError('forecast_start must be aligned to a whole hour')
    return t

def make_features(history,forecast_start):
    a=validate_history(history)
    t=parse_time(forecast_start) if isinstance(forecast_start,str) else forecast_start
    hour=t.hour;weekday=t.weekday()
    return np.array([a[-1],a[-2],a[-3],a[-6],a[-12],a[-24],
                     a[-3:].mean(),a[-6:].mean(),a.mean(),a.std(ddof=0),
                     math.sin(2*math.pi*hour/24),math.cos(2*math.pi*hour/24),
                     math.sin(2*math.pi*weekday/7),math.cos(2*math.pi*weekday/7),
                     float(weekday>=5)],dtype=np.float32)
