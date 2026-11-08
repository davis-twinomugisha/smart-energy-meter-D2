"""Send explicitly labelled recorded-data replay over HTTP. No hardware sensing is claimed."""
import argparse,json,time,urllib.request

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',default='http://127.0.0.1:8765')
    p.add_argument('--samples',type=int,default=3);args=p.parse_args()
    with urllib.request.urlopen(args.url+'/api/examples',timeout=10) as r:examples=json.load(r)
    for i in range(args.samples):
        example=dict(examples[i%len(examples)]);example['node_id']='HOST_REPLAY_01'
        example['data_mode']='public_data_replay'
        data=json.dumps(example).encode()
        request=urllib.request.Request(args.url+'/api/telemetry',data=data,headers={'Content-Type':'application/json'})
        start=time.perf_counter()
        with urllib.request.urlopen(request,timeout=10) as r:result=json.load(r)
        print(json.dumps({'mode':result['data_mode'],'next_hour_kwh':result['next_hour_kwh'],
                          'HTTP_round_trip_ms':(time.perf_counter()-start)*1000,
                          'payload_bytes':len(data)}))

if __name__=='__main__':main()
