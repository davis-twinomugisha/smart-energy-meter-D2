"""Local HTTP research demo. Default binds to loopback. No utility or account access."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from datetime import datetime
import argparse,json,threading,time
import joblib
import numpy as np
import pandas as pd
from .features import make_features,validate_history,parse_time
from .depletion import forecast_path,baseline_paths,exhaustion_time

ROOT=Path(__file__).resolve().parents[1]

class Predictor:
    def __init__(self):
        self.model=joblib.load(ROOT/'models/selected_model.joblib')
        if hasattr(self.model,'n_jobs'):self.model.n_jobs=1
        self.evaluation=json.loads((ROOT/'results/evaluation.json').read_text())
        self.lock=threading.Lock()

    def predict(self,payload):
        if not isinstance(payload,dict):raise ValueError('JSON body must be an object')
        history=validate_history(payload.get('history_kwh',[]))
        start=parse_time(payload.get('forecast_start'))
        beginning=time.perf_counter_ns()
        path=forecast_path(self.model,history,start)
        baselines=baseline_paths(history)
        elapsed=(time.perf_counter_ns()-beginning)/1e6
        balance=payload.get('balance_kwh')
        balance_result=None
        if balance is not None:
            crossing=exhaustion_time(path,balance)
            balance_result={'starting_balance_kwh':float(balance),'balance_source':'manually supplied, not utility verified',
                            'assumes_no_topups':True,'forecast_horizon_hours':24,
                            'predicted_depletion_hours':crossing,
                            'warning_within_6h':crossing is not None and crossing<=6,
                            'beyond_forecast_horizon':crossing is None,
                            'within_hour_assumption':'uniform consumption in each forecast hour',
                            'baseline_depletion_hours':{name:exhaustion_time(p,balance) for name,p in baselines.items()}}
        return {'forecast_start':start.isoformat(),'model':self.evaluation['selected_configuration'],
                'history_hours':24,'next_hour_kwh':path[0],'forecast_24h_kwh':path,
                'baselines_next_hour_kwh':{name:p[0] for name,p in baselines.items()},
                'baselines_24h_kwh':baselines,'balance_scenario':balance_result,
                'host_forecast_compute_ms':elapsed,
                'data_mode':payload.get('data_mode','unspecified input'),
                'scope':'Experimental consumption forecast; not a Yaka balance lookup or validated Ugandan forecast.'}

    def examples(self):
        hourly=pd.read_csv(ROOT/'data/processed/hourly_energy.csv',parse_dates=['hour_start']).set_index('hour_start').energy_kwh
        table=pd.read_csv(ROOT/'data/processed/supervised_hourly.csv',parse_dates=['hour_start'])
        test=table[table.split=='test'].reset_index(drop=True)
        output=[]
        for label,i in [('Beginning of test',0),('Middle of test',len(test)//2),('Later test period',len(test)-25)]:
            t=test.hour_start.iloc[i]
            history=hourly.reindex(pd.date_range(t-pd.Timedelta(hours=24),periods=24,freq='h')).to_numpy()
            if not np.isfinite(history).all():continue
            output.append({'label':label,'forecast_start':t.isoformat(),'history_kwh':history.tolist(),
                           'balance_kwh':5,'data_mode':'public_data_replay',
                           'provenance':'Recorded UCI household data from France; assigned 5 kWh balance is synthetic.'})
        return output

def make_handler(predictor):
    class Handler(BaseHTTPRequestHandler):
        def reply(self,status,value,content_type='application/json'):
            data=json.dumps(value,allow_nan=False).encode() if content_type=='application/json' else value
            self.send_response(status);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.path in ('/','/index.html'):
                return self.reply(200,(ROOT/'web/index.html').read_bytes(),'text/html; charset=utf-8')
            if self.path=='/api/status':
                return self.reply(200,{'state':'software demo ready','hardware_connected':False,
                      'source':'UCI, one French household','evaluation':predictor.evaluation,
                      'hardware_timing':'pending','wireless_radio_test':'pending'})
            if self.path=='/api/examples':return self.reply(200,predictor.examples())
            return self.reply(404,{'error':'Unknown endpoint'})
        def do_POST(self):
            if self.path not in ('/api/predict','/api/telemetry'):return self.reply(404,{'error':'Unknown endpoint'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length<1 or length>32768:raise ValueError('Body must be 1 to 32768 bytes')
                if self.headers.get_content_type()!='application/json':raise ValueError('Use application/json')
                payload=json.loads(self.rfile.read(length))
                result=predictor.predict(payload)
                if self.path=='/api/telemetry':
                    mode=payload.get('data_mode')
                    if mode not in ('public_data_replay','sensor_live_unverified'):raise ValueError('Telemetry must declare its data_mode')
                    edge=payload.get('edge_prediction_kwh')
                    if edge is not None:
                        if isinstance(edge,bool) or not np.isfinite(float(edge)) or float(edge)<0:raise ValueError('Invalid edge prediction')
                        result['edge_host_absolute_difference_kwh']=abs(float(edge)-result['next_hour_kwh'])
                    runtime=ROOT/'runtime';runtime.mkdir(exist_ok=True)
                    with predictor.lock,(runtime/'telemetry.jsonl').open('a') as f:
                        f.write(json.dumps({'received_at':datetime.now().isoformat(),'node_id':str(payload.get('node_id','unnamed'))[:80],
                                            'data_mode':mode,'next_hour_kwh':result['next_hour_kwh']})+'\n')
                return self.reply(200,result)
            except (ValueError,TypeError,KeyError,OverflowError) as error:
                return self.reply(400,{'error':str(error)})
        def log_message(self,format,*args):pass
    return Handler

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    server=ThreadingHTTPServer((args.host,args.port),make_handler(Predictor()))
    print(f'Energy D2 software demo at http://{args.host}:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
