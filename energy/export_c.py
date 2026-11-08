"""Export sklearn trees to portable C and check float32 inference equivalence on host."""
from pathlib import Path
import ctypes,json,subprocess,time
import numpy as np
import pandas as pd
import joblib
from .features import FEATURE_NAMES,make_features

ROOT=Path(__file__).resolve().parents[1]

def write_model(model,path,prefix='energy_model'):
    estimators=list(model.estimators_) if hasattr(model,'estimators_') else [model]
    lines=['#pragma once','#include <stdint.h>','#include <stddef.h>',
           f'#define ENERGY_FEATURE_COUNT {len(FEATURE_NAMES)}',
           '// Features and thresholds use float32. This is C export, not integer quantization.',
           '// Feature order: '+', '.join(FEATURE_NAMES)]
    bytes_est=0;nodes=0
    for j,estimator in enumerate(estimators):
        tree=estimator.tree_;n=tree.node_count;nodes+=n
        if n>=32767:raise ValueError('Tree exceeds int16 index capacity')
        threshold=tree.threshold.astype(np.float32)
        up=threshold.astype(np.float64)>tree.threshold
        threshold[up]=np.nextafter(threshold[up],np.float32(-np.inf),dtype=np.float32)
        arrays={'left':('int16_t',tree.children_left),'right':('int16_t',tree.children_right),
                'feature':('int8_t',tree.feature),'threshold':('float',threshold),
                'value':('float',tree.value[:,0,0].astype(np.float32))}
        for name,(typ,values) in arrays.items():
            if typ=='float':text=','.join(float(v).hex()+'f' for v in values)
            else:text=','.join(str(int(v)) for v in values)
            lines.append(f'static const {typ} {prefix}_{j}_{name}[{n}] = {{{text}}};')
            bytes_est+=n*({'int16_t':2,'int8_t':1,'float':4}[typ])
        lines.append(f'''static inline float {prefix}_tree_{j}(const float *x) {{
 int16_t i=0;
 while ({prefix}_{j}_feature[i]>=0) {{
  int feature={prefix}_{j}_feature[i];
  i=(x[feature]<={prefix}_{j}_threshold[i])?{prefix}_{j}_left[i]:{prefix}_{j}_right[i];
 }}
 return {prefix}_{j}_value[i];
}}''')
    total='+'.join(f'(double){prefix}_tree_{j}(x)' for j in range(len(estimators)))
    lines.append(f'static inline float {prefix}_predict(const float *x) {{ return (float)(({total})/{len(estimators)}.0); }}')
    path.write_text('\n'.join(lines)+'\n')
    return {'trees':len(estimators),'nodes':nodes,'constant_array_payload_bytes':bytes_est,'header_source_bytes':path.stat().st_size,
            'constant_payload_note':'Sum of constant array element sizes. Target-board compiled flash and RAM have not been measured.'}

def main():
    out=ROOT/'deployment';out.mkdir(exist_ok=True)
    model=joblib.load(ROOT/'models/selected_model.joblib')
    stats=write_model(model,out/'energy_model.h')
    small=joblib.load(ROOT/'models/decision_tree.joblib')
    stats['compact_tree_alternative']=write_model(small,out/'compact_tree_model.h','compact_tree_model')
    helper='''#include "energy_model.h"
#include "compact_tree_model.h"
#include "energy_features.h"
extern "C" float predict_one(const float *x){return energy_model_predict(x);}
extern "C" float compact_one(const float *x){return compact_tree_model_predict(x);}
extern "C" void features_one(const float *h,int hour,int weekday,float *x){energy_features(h,hour,weekday,x);}
extern "C" double benchmark(const float *x,int rows,int count){
 volatile float sink=0;
 for(int i=0;i<count;i++)sink=energy_model_predict(x+(i%rows)*ENERGY_FEATURE_COUNT);
 return sink;
}
'''
    (out/'host_wrapper.cpp').write_text(helper)
    shared=out/'host_model.so'
    cmd=['g++','-std=c++17','-O2','-shared','-fPIC',str(out/'host_wrapper.cpp'),'-o',str(shared)]
    subprocess.run(cmd,check=True,capture_output=True)
    lib=ctypes.CDLL(str(shared));ptr=ctypes.POINTER(ctypes.c_float)
    lib.predict_one.argtypes=[ptr];lib.predict_one.restype=ctypes.c_float
    lib.compact_one.argtypes=[ptr];lib.compact_one.restype=ctypes.c_float
    lib.features_one.argtypes=[ptr,ctypes.c_int,ctypes.c_int,ptr]
    lib.benchmark.argtypes=[ptr,ctypes.c_int,ctypes.c_int];lib.benchmark.restype=ctypes.c_double
    table=pd.read_csv(ROOT/'data/processed/supervised_hourly.csv',parse_dates=['hour_start'])
    X=np.ascontiguousarray(table[FEATURE_NAMES].to_numpy(dtype=np.float32))
    expected=model.predict(X)
    got=np.array([lib.predict_one(row.ctypes.data_as(ptr)) for row in X])
    error=np.abs(got-expected)
    if error.max()>1e-5:raise AssertionError(f'C/Python model mismatch: {error.max()}')
    compact=np.array([lib.compact_one(row.ctypes.data_as(ptr)) for row in X])
    compact_error=float(np.max(np.abs(compact-small.predict(X))))
    if compact_error>1e-5:raise AssertionError('Compact tree C/Python mismatch')
    stats['compact_tree_alternative']['host_parity_rows']=len(X)
    stats['compact_tree_alternative']['max_absolute_prediction_difference_kwh']=compact_error
    # Check generated features and the entire combined feature+model path independently.
    hourly=pd.read_csv(ROOT/'data/processed/hourly_energy.csv',parse_dates=['hour_start']).set_index('hour_start').energy_kwh
    selected=table.iloc[np.linspace(0,len(table)-1,150,dtype=int)]
    feature_errors=[];prediction_errors=[]
    for row in selected.itertuples():
        t=row.hour_start
        h=hourly.reindex(pd.date_range(t-pd.Timedelta(hours=24),periods=24,freq='h')).to_numpy(dtype=np.float32)
        x=np.zeros(len(FEATURE_NAMES),dtype=np.float32)
        lib.features_one(h.ctypes.data_as(ptr),t.hour,t.weekday(),x.ctypes.data_as(ptr))
        reference=make_features(h,t.to_pydatetime())
        feature_errors.append(float(np.max(np.abs(x-reference))))
        c_result=lib.predict_one(x.ctypes.data_as(ptr))
        prediction_errors.append(abs(float(c_result)-float(model.predict(reference.reshape(1,-1))[0])))
    if max(feature_errors)>2e-5:raise AssertionError('C feature mismatch')
    if max(prediction_errors)>1e-5:raise AssertionError('Combined C feature/prediction mismatch')
    # Batch timing avoids claiming that per-call Python overhead is model compute time.
    count=100000;timings=[]
    for _ in range(12):
        start=time.perf_counter_ns();lib.benchmark(X.ctypes.data_as(ptr),len(X),count)
        timings.append((time.perf_counter_ns()-start)/count/1000)
    stats.update({'host_compiler_command':cmd,'host_parity_rows':len(X),'max_absolute_prediction_difference_kwh':float(error.max()),
                  'combined_feature_tests':len(selected),'max_feature_difference':max(feature_errors),
                  'max_combined_prediction_difference_kwh':max(prediction_errors),
                  'host_benchmark_protocol':'12 batches of 100000 calls cycling all feature rows; includes loop/index overhead; host only',
                  'host_batch_average_inference_us_median':float(np.median(timings)),
                  'host_batch_average_inference_us_min':float(np.min(timings)),
                  'host_batch_average_inference_us_max':float(np.max(timings)),
                  'board_compilation':'not performed; no ESP32 toolchain or connected board',
                  'board_inference_ms':None,'board_flash_bytes':None,'board_ram_bytes':None,'electrical_energy_per_inference':None})
    (ROOT/'results/deployment_checks.json').write_text(json.dumps(stats,indent=2))
    print(json.dumps(stats,indent=2))

if __name__=='__main__':main()
