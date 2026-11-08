"""Publication figures from saved measured-data results. No simulated sensor values."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT=Path(__file__).resolve().parents[1]
LABELS={'mean_24h':'24-hour mean','persistence':'Persistence','same_hour_yesterday':'Same hour yesterday','decision_tree':'Decision tree','random_forest':'Random forest','selected_ml':'Random forest'}
def main():
    out=ROOT/'figures';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','savefig.dpi':180})
    metrics=pd.read_csv(ROOT/'results/test_metrics.csv')
    fig,ax=plt.subplots(figsize=(8,3.5),layout='constrained')
    colors=['#829493']*3+['#3d8783','#145a50']
    bars=ax.barh([LABELS[x] for x in metrics.method],metrics.MAE_kWh,color=colors)
    ax.invert_yaxis();ax.set(xlabel='MAE (kWh per forecast hour)',title='Held-out next-hour forecast error, 4,805 hours')
    for b,v in zip(bars,metrics.MAE_kWh):ax.text(v+.008,b.get_y()+b.get_height()/2,f'{v:.3f}',va='center')
    ax.set_xlim(0,.64);ax.grid(axis='x',alpha=.15);fig.savefig(out/'01_test_mae.png');plt.close(fig)
    pred=pd.read_csv(ROOT/'results/test_predictions.csv',parse_dates=['hour_start']).set_index('hour_start')
    # Prespecified first 168 chronological test hours, keeping gaps visible.
    sample=pred.reindex(pd.date_range(pred.index.min(),periods=168,freq='h'))
    fig,ax=plt.subplots(figsize=(9,3.6),layout='constrained')
    for col,label,c,alpha in [('actual_kwh','Measured energy','#202d36',.95),('random_forest','Random forest','#19776b',.95),('mean_24h','24-hour mean','#c8782b',.8)]:
        ax.plot(sample.index,sample[col],label=label,color=c,lw=1.3,alpha=alpha)
    ax.set(title='First seven days of the frozen test period',ylabel='Hourly energy (kWh)',xlabel='Time, original source clock')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'));ax.legend(ncol=3,frameon=False);ax.grid(alpha=.15)
    fig.savefig(out/'02_test_forecast.png');plt.close(fig)
    table=pd.read_csv(ROOT/'data/processed/supervised_hourly.csv',parse_dates=['hour_start'])
    fig,ax=plt.subplots(figsize=(9,1.9),layout='constrained')
    for name,c in [('train','#648dba'),('validation','#d9a44c'),('test','#24796a')]:
        block=table[table.split==name];left=mdates.date2num(block.hour_start.min());right=mdates.date2num(block.hour_start.max())
        ax.barh(0,right-left,left=left,height=.5,color=c,label=f'{name.title()}: {len(block):,}')
    ax.set_yticks([]);ax.xaxis_date();ax.set(title='Chronological split, no shuffled target hours',xlabel='Original source clock')
    ax.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,1),frameon=False);fig.savefig(out/'03_temporal_split.png');plt.close(fig)
    residual=pred.random_forest-pred.actual_kwh
    fig,(ax,ay)=plt.subplots(1,2,figsize=(9,3.5),layout='constrained')
    ax.scatter(pred.actual_kwh,pred.random_forest,s=5,alpha=.15,color='#19776b',rasterized=True)
    limit=float(max(pred.actual_kwh.max(),pred.random_forest.max()));ax.plot([0,limit],[0,limit],color='#b67328',lw=1)
    ax.set(xlabel='Measured energy (kWh)',ylabel='Forecast energy (kWh)',title='Measured versus forecast')
    ay.hist(residual,bins=50,color='#19776b');ay.axvline(0,color='#b67328',lw=1)
    ay.set(xlabel='Forecast minus measured (kWh)',ylabel='Test hours',title=f'Residuals, mean {residual.mean():.3f} kWh')
    fig.savefig(out/'04_error_diagnostics.png');plt.close(fig)
    scenario=json.loads((ROOT/'results/constructed_scenario_metrics.json').read_text())
    d=pd.DataFrame(scenario['methods']);fig,(ax,ay)=plt.subplots(1,2,figsize=(9,3.4),layout='constrained')
    labels=[LABELS[x] for x in d.method]
    ax.barh(labels,d.MAE_hours_common_subset,color=['#829493']*3+['#19776b']);ax.invert_yaxis()
    ax.set(xlabel='Depletion-time MAE (hours)',title='Common uncensored subset, n=553')
    x=np.arange(len(d));width=.36
    ay.bar(x-width/2,d.warning_precision,width,label='Precision',color='#648dba')
    ay.bar(x+width/2,d.warning_recall,width,label='Recall',color='#19776b')
    ay.set_xticks(x,labels,rotation=25,ha='right');ay.set(ylim=(0,1.1),title='Six-hour warnings, 772 cases');ay.legend(frameon=False)
    fig.suptitle('Constructed balances on measured consumption, not real prepaid events',fontsize=11)
    fig.savefig(out/'05_constructed_scenarios.png');plt.close(fig)
    print('Created five figures from frozen experiment outputs.')

if __name__=='__main__':main()
