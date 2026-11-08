from pathlib import Path
from datetime import datetime
import hashlib,json,platform,time,zipfile
import numpy as np
import pandas as pd
import sklearn,joblib
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from .features import FEATURE_NAMES,make_features
from .depletion import forecast_path,baseline_paths,exhaustion_time

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/household_power_consumption.zip'
EXPECTED_SHA='9f84b46ade8a2d8e1286ec4b2b6c2987a45a755c59f263be3b3b3d10dfbda3ff'
SEED=20261106

def save_json(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,allow_nan=False))

def prepare():
    if hashlib.sha256(RAW.read_bytes()).hexdigest()!=EXPECTED_SHA:raise ValueError('Raw archive checksum mismatch')
    with zipfile.ZipFile(RAW) as z:
        with z.open('household_power_consumption.txt') as f:
            d=pd.read_csv(f,sep=';',usecols=['Date','Time','Global_active_power'],na_values=['?'])
    stamp=pd.to_datetime(d.Date+' '+d.Time,format='%d/%m/%Y %H:%M:%S',errors='raise')
    values=pd.to_numeric(d.Global_active_power,errors='coerce')
    invalid=~np.isfinite(values) | values.lt(0)
    minute=pd.Series(values.where(~invalid).to_numpy(),index=stamp,name='power_kw').sort_index()
    if minute.index.has_duplicates:raise ValueError('Duplicate timestamps require explicit resolution')
    counts=minute.resample('h').count()
    energy=(minute.resample('h').sum(min_count=60)/60.0).where(counts.eq(60))
    hourly=pd.DataFrame({'energy_kwh':energy,'valid_minutes':counts})
    hourly.index.name='hour_start'
    f=pd.DataFrame(index=hourly.index)
    for lag in [1,2,3,6,12,24]:f[f'lag_{lag}']=energy.shift(lag)
    for window in [3,6,24]:f[f'mean_{window}']=energy.shift().rolling(window,min_periods=window).mean()
    f['std_24']=energy.shift().rolling(24,min_periods=24).std(ddof=0)
    f['hour_sin']=np.sin(2*np.pi*f.index.hour/24)
    f['hour_cos']=np.cos(2*np.pi*f.index.hour/24)
    f['weekday_sin']=np.sin(2*np.pi*f.index.dayofweek/7)
    f['weekday_cos']=np.cos(2*np.pi*f.index.dayofweek/7)
    f['weekend']=(f.index.dayofweek>=5).astype(float)
    f['target_kwh']=energy
    n=len(hourly);first=int(n*.70);second=int(n*.85)
    cut1=hourly.index[first];cut2=hourly.index[second]
    f['split']=np.where(f.index<cut1,'train',np.where(f.index<cut2,'validation','test'))
    # All 24 history hours are required even though only some are individual lag columns.
    eligible=energy.shift().rolling(24,min_periods=24).count().eq(24)&f.target_kwh.notna()
    table=f.loc[eligible].dropna().copy()
    out=ROOT/'data/processed';out.mkdir(parents=True,exist_ok=True)
    hourly.to_csv(out/'hourly_energy.csv',float_format='%.10g')
    table.to_csv(out/'supervised_hourly.csv',float_format='%.10g')
    audit={
        'raw_rows':len(d),'raw_missing_or_invalid_power_rows':int(invalid.sum()),
        'first_minute':str(minute.index[0]),'last_minute':str(minute.index[-1]),
        'timestamp_duplicates':0,'total_hour_bins':n,'complete_hour_bins':int(energy.notna().sum()),
        'incomplete_hour_bins':int(energy.isna().sum()),'usable_supervised_rows':len(table),
        'excluded_from_supervised':n-len(table),'imputed_values':0,
        'validation_start':str(cut1),'test_start':str(cut2),
        'splits':{name:{'rows':int((table.split==name).sum()),
                        'start':str(table.index[table.split==name][0]),'end':str(table.index[table.split==name][-1])}
                  for name in ['train','validation','test']},
        'raw_sha256':EXPECTED_SHA,'source_country':'France','source_households':1,
        'time_basis':'Original source clock retained as timezone-naive. No Uganda timezone or locale conversion is claimed.'}
    save_json(ROOT/'results/data_audit.json',audit)
    print('DATA',json.dumps(audit),flush=True)
    return hourly,table,audit

def metrics(y,p):
    return {'MAE_kWh':float(mean_absolute_error(y,p)),
            'RMSE_kWh':float(np.sqrt(mean_squared_error(y,p))),
            'R2':float(r2_score(y,p)),
            'WAPE_percent':float(np.abs(np.asarray(y)-p).sum()/np.abs(y).sum()*100)}

def train(hourly,table):
    from itertools import product
    modeldir=ROOT/'models';modeldir.mkdir(exist_ok=True)
    t=table[table.split=='train'];v=table[table.split=='validation'];test=table[table.split=='test']
    X=t[FEATURE_NAMES].to_numpy(dtype=np.float32);y=t.target_kwh.to_numpy()
    XV=v[FEATURE_NAMES].to_numpy(dtype=np.float32);yv=v.target_kwh.to_numpy()
    rows=[];candidates={}
    for depth,leaf in product([3,5,7,9],[12,48]):
        name=f'tree_d{depth}_leaf{leaf}'
        model=DecisionTreeRegressor(max_depth=depth,min_samples_leaf=leaf,random_state=SEED)
        model.fit(X,y);score=metrics(yv,model.predict(XV))
        rows.append({'name':name,'family':'decision_tree','params':model.get_params(),**score});candidates[name]=model
    for count,depth in product([16,32],[6,8]):
        name=f'forest_n{count}_d{depth}'
        model=RandomForestRegressor(n_estimators=count,max_depth=depth,min_samples_leaf=12,
                                    random_state=SEED,n_jobs=2)
        model.fit(X,y);score=metrics(yv,model.predict(XV))
        rows.append({'name':name,'family':'random_forest','params':model.get_params(),**score});candidates[name]=model
    chosen=min(rows,key=lambda r:(r['MAE_kWh'],r['name']))
    winners={family:min([r for r in rows if r['family']==family],key=lambda r:r['MAE_kWh']) for family in ['decision_tree','random_forest']}
    selection={'selection_metric':'validation MAE only','selected_configuration':chosen,
               'all_validation_configurations':rows,'test_used_for_selection':False}
    save_json(ROOT/'results/model_selection.json',selection)
    pd.DataFrame([{k:value for k,value in r.items() if k!='params'} for r in rows]).to_csv(ROOT/'results/validation_search.csv',index=False)
    combined=table[table.split.isin(['train','validation'])]
    XT=test[FEATURE_NAMES].to_numpy(dtype=np.float32);yt=test.target_kwh.to_numpy()
    predictions={name:test[col].to_numpy() for name,col in [('mean_24h','mean_24'),('persistence','lag_1'),('same_hour_yesterday','lag_24')]}
    fitted={}
    for family,row in winners.items():
        model=candidates[row['name']]
        model.fit(combined[FEATURE_NAMES].to_numpy(dtype=np.float32),combined.target_kwh.to_numpy())
        fitted[family]=model;predictions[family]=model.predict(XT)
        joblib.dump(model,modeldir/f'{family}.joblib')
    chosen_model=fitted[chosen['family']]
    joblib.dump(chosen_model,modeldir/'selected_model.joblib')
    baseline_val={name:metrics(yv,v[col].to_numpy()) for name,col in [('mean_24h','mean_24'),('persistence','lag_1'),('same_hour_yesterday','lag_24')]}
    score_rows=[]
    for name,p in predictions.items():score_rows.append({'method':name,**metrics(yt,p),'selected_ml':name==chosen['family']})
    scores=pd.DataFrame(score_rows)
    scores.to_csv(ROOT/'results/test_metrics.csv',index=False)
    pd.DataFrame({'hour_start':test.index,'actual_kwh':yt,**predictions}).to_csv(ROOT/'results/test_predictions.csv',index=False,float_format='%.9g')
    # Paired resampling of daily blocks, preserving within-day serial dependence.
    selected_pred=predictions[chosen['family']]
    paired=pd.DataFrame({'baseline':np.abs(yt-predictions['mean_24h']),
                         'model':np.abs(yt-selected_pred)},index=test.index)
    blocks=paired.groupby(paired.index.date).agg(['sum','count'])
    rng=np.random.default_rng(SEED);estimates=[]
    for _ in range(2000):
        ids=rng.integers(0,len(blocks),len(blocks));a=blocks.iloc[ids]
        base=a[('baseline','sum')].sum()/a[('baseline','count')].sum()
        mod=a[('model','sum')].sum()/a[('model','count')].sum()
        estimates.append((base-mod)/base*100)
    main=metrics(yt,selected_pred);base=metrics(yt,predictions['mean_24h'])
    improvement=(base['MAE_kWh']-main['MAE_kWh'])/base['MAE_kWh']*100
    result={'selected_family':chosen['family'],'selected_configuration':chosen['name'],
            'test_rows':len(test),'test_metrics':score_rows,'validation_baseline_metrics':baseline_val,
            'primary_MAE_improvement_percent':float(improvement),
            'daily_block_bootstrap_95pct_interval_percent':[float(np.quantile(estimates,.025)),float(np.quantile(estimates,.975))],
            'predeclared_10pct_target_met':bool(improvement>=10),
            'generalization_scope':'Held-out future hours from the same French household, not independent Ugandan households.'}
    save_json(ROOT/'results/evaluation.json',result)
    save_json(modeldir/'feature_schema.json',{'feature_names':FEATURE_NAMES,'history_hours':24,'target':'next full hour energy, kWh','feature_dtype':'float32','scaler':None,'missing_history_policy':'reject until 24 consecutive complete valid hours are available'})
    save_json(modeldir/'baseline_config.json',{'methods':['mean_24h','persistence','same_hour_yesterday'],'history_hours':24})
    print('TEST',scores.to_string(index=False),flush=True)
    print('SELECTED',chosen['name'],'MAE improvement',improvement,flush=True)
    return chosen_model,result

def scenarios(hourly,table,model):
    energy=hourly.energy_kwh
    test_start=pd.Timestamp(json.loads((ROOT/'results/data_audit.json').read_text())['test_start'])
    origins=hourly.loc[test_start:].index[::24]
    eligible=set(table[table.split=='test'].index)
    records=[];n_origins=0
    for timestamp in origins:
        if timestamp not in eligible:continue
        hist=energy.reindex(pd.date_range(timestamp-pd.Timedelta(hours=24),periods=24,freq='h'))
        future=energy.reindex(pd.date_range(timestamp,periods=24,freq='h'))
        if hist.isna().any() or future.isna().any():continue
        n_origins+=1
        paths=baseline_paths(hist.to_numpy())
        paths['selected_ml']=forecast_path(model,hist.to_numpy(),timestamp.to_pydatetime())
        for balance in [2.,5.,10.,20.]:
            truth=exhaustion_time(future.to_numpy(),balance)
            for method,path in paths.items():
                predicted=exhaustion_time(path,balance)
                records.append({'origin':str(timestamp),'assigned_balance_kwh':balance,'method':method,
                                'actual_constructed_depletion_hours':truth,'predicted_depletion_hours':predicted,
                                'actual_within_6h':truth is not None and truth<=6,
                                'warning_within_6h':predicted is not None and predicted<=6})
    d=pd.DataFrame(records);d.to_csv(ROOT/'results/constructed_balance_scenarios.csv',index=False)
    wide=d.pivot(index=['origin','assigned_balance_kwh'],columns='method',values='predicted_depletion_hours')
    true=d.drop_duplicates(['origin','assigned_balance_kwh']).set_index(['origin','assigned_balance_kwh']).actual_constructed_depletion_hours
    common=wide.notna().all(axis=1)&true.notna()
    summaries=[]
    for method,g in d.groupby('method'):
        actual=g.actual_constructed_depletion_hours.notna();pred=g.predicted_depletion_hours.notna()
        tp=int((g.actual_within_6h & g.warning_within_6h).sum())
        fp=int((~g.actual_within_6h & g.warning_within_6h).sum())
        fn=int((g.actual_within_6h & ~g.warning_within_6h).sum())
        summaries.append({'method':method,'scenarios':len(g),'origins':n_origins,
                          'actual_depletion_within_24h':int(actual.sum()),
                          'predicted_depletion_within_24h':int(pred.sum()),
                          'missed_24h_depletion':int((actual&~pred).sum()),
                          'false_24h_depletion':int((~actual&pred).sum()),
                          'common_uncensored_scenarios':int(common.sum()),
                          'MAE_hours_common_subset':float(np.abs(wide.loc[common,method]-true.loc[common]).mean()) if common.any() else None,
                          'warning_TP':tp,'warning_FP':fp,'warning_FN':fn,
                          'warning_precision':tp/(tp+fp) if tp+fp else None,
                          'warning_recall':tp/(tp+fn) if tp+fn else None})
    save_json(ROOT/'results/constructed_scenario_metrics.json',{
        'scenario_type':'Assigned starting balances on held-out measured consumption, no observed prepaid balances or top-ups',
        'horizon_hours':24,'warning_horizon_hours':6,'origins':n_origins,'methods':summaries,
        'limitations':'Hours MAE uses common uncensored subset only. Coverage/miss counts accompany it. Repeated balances share the same origin and are not independent household events.'})
    print('SCENARIOS',n_origins,'daily origins',flush=True)

def main():
    for p in ['models','results','figures','data/processed']: (ROOT/p).mkdir(parents=True,exist_ok=True)
    save_json(ROOT/'results/environment.json',{'python':platform.python_version(),'platform':platform.platform(),'numpy':np.__version__,'pandas':pd.__version__,'scikit_learn':sklearn.__version__,'joblib':joblib.__version__})
    hourly,table,audit=prepare();model,evaluation=train(hourly,table);scenarios(hourly,table,model)

if __name__=='__main__':main()
