"""Run software checks and measure host-loopback HTTP, not a wireless radio."""
from pathlib import Path
import ctypes,io,json,sys,threading,time,unittest,urllib.request
from http.server import ThreadingHTTPServer
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from energy.server import Predictor,make_handler

def main():
    stream=io.StringIO();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (ROOT/'results/software_test_log.txt').write_text(stream.getvalue())
    if not result.wasSuccessful():raise SystemExit(stream.getvalue())
    predictor=Predictor();server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(predictor))
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    url='http://127.0.0.1:'+str(server.server_port)+'/api/telemetry'
    examples=predictor.examples();ptr=ctypes.POINTER(ctypes.c_float)
    lib=ctypes.CDLL(str(ROOT/'deployment/host_model.so'))
    lib.features_one.argtypes=[ptr,ctypes.c_int,ctypes.c_int,ptr]
    lib.predict_one.argtypes=[ptr];lib.predict_one.restype=ctypes.c_float
    records=[]
    try:
        for i in range(20):
            example=dict(examples[i%len(examples)])
            from datetime import datetime
            t=datetime.fromisoformat(example['forecast_start'])
            h=np.array(example['history_kwh'],dtype=np.float32);features=np.zeros(15,dtype=np.float32)
            lib.features_one(h.ctypes.data_as(ptr),t.hour,t.weekday(),features.ctypes.data_as(ptr))
            example['edge_prediction_kwh']=float(lib.predict_one(features.ctypes.data_as(ptr)))
            example['node_id']='HOST_C_REPLAY_01'
            body=json.dumps(example,allow_nan=False,separators=(',',':')).encode()
            request=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json'})
            start=time.perf_counter_ns()
            with urllib.request.urlopen(request,timeout=10) as response:
                response_bytes=response.read();value=json.loads(response_bytes);status=response.status
            elapsed=(time.perf_counter_ns()-start)/1e6
            records.append({'sequence':i+1,'status':status,'request_body_bytes':len(body),'response_body_bytes':len(response_bytes),
                            'roundtrip_ms':elapsed,'host_recursive_forecast_ms':value['host_forecast_compute_ms'],
                            'c_host_next_hour_difference_kwh':value['edge_host_absolute_difference_kwh']})
        if max(x['c_host_next_hour_difference_kwh'] for x in records)>1e-5:raise AssertionError('HTTP C/host mismatch')
    finally:server.shutdown();server.server_close();worker.join()
    timings=[r['roundtrip_ms'] for r in records]
    output={'software_tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'http_transport':'Host loopback TCP/HTTP; no physical wireless link',
            'http_requests':len(records),'successful_requests':sum(r['status']==200 for r in records),
            'host_loopback_roundtrip_ms_median':float(np.median(timings)),
            'host_loopback_roundtrip_ms_p95':float(np.percentile(timings,95)),
            'request_body_bytes_min':min(r['request_body_bytes'] for r in records),
            'request_body_bytes_max':max(r['request_body_bytes'] for r in records),
            'max_C_host_difference_kwh':max(r['c_host_next_hour_difference_kwh'] for r in records),
            'board_inference_tested':False,'sensor_connected':False,'physical_wireless_tested':False,'requests':records}
    (ROOT/'results/software_verification.json').write_text(json.dumps(output,indent=2))
    print(json.dumps({k:v for k,v in output.items() if k!='requests'},indent=2))

if __name__=='__main__':main()
