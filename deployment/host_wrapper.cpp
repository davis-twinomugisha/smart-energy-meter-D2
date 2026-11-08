#include "energy_model.h"
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
